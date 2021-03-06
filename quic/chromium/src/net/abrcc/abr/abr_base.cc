#include "net/abrcc/abr/abr_base.h"


const int SECOND = 1000; 

const int RESERVOIR = 5 * SECOND;
const int CUSHION = 10 * SECOND;


// debug utilities
static void log_segment(abr_schema::Segment &segment) {
  switch (segment.state) {
    case abr_schema::Segment::PROGRESS:
      QUIC_LOG(WARNING) << "segment " << segment.index 
                        << " [progress] " << 1.0 * segment.loaded / segment.total;
      break;
    case abr_schema::Segment::DOWNLOADED:
      QUIC_LOG(WARNING) << "segment " << segment.index << " [downloaded]";
      break;
    case abr_schema::Segment::LOADING:
      QUIC_LOG(WARNING) << "segment " << segment.index << " [loading]";
      break;
  }
}


namespace quic {

SegmentProgressAbr::SegmentProgressAbr(const std::shared_ptr<DashBackendConfig>& config) : 
  config(config), decision_index(1), last_timestamp(0) {

  // compute segments
  segments = std::vector< std::vector<VideoInfo> >();
  for (int i = 0; i < int(config->video_configs.size()); ++i) {
    for (auto &video_config : config->video_configs) {
      std::string resource = "/video" + std::to_string(i);
      if (resource == video_config->resource) {
        std::vector<VideoInfo> info;
        for (auto &x : video_config->video_info) {
          info.push_back(VideoInfo(
            x->start_time,
            x->vmaf,
            x->size
          ));  
        }
        segments.push_back(info);
      }
    }
  }

  // compute bitrate array
  bitrate_array = std::vector<int>();
  for (auto &video_config : config->video_configs) {
    bitrate_array.push_back(video_config->quality);
  }
  sort(bitrate_array.begin(), bitrate_array.end());
}
SegmentProgressAbr::~SegmentProgressAbr() {}

void SegmentProgressAbr::update_segment(abr_schema::Segment segment) {
  last_segment[segment.index] = segment;
  
  QUIC_LOG(WARNING) << "[segment update @ " << segment.index << "]";
  log_segment(segment);
}

void SegmentProgressAbr::registerAbort(const int index) {
  aborted.insert(index);  
}

void SegmentProgressAbr::registerMetrics(const abr_schema::Metrics &metrics) {
  for (const auto& segment : metrics.segments) {
    last_timestamp = std::max(last_timestamp, segment->timestamp);

    switch(segment->state) {
      case abr_schema::Segment::LOADING:
        break;
      case abr_schema::Segment::DOWNLOADED:
        if (last_segment.find(segment->index) == last_segment.end() ||
            last_segment[segment->index].state == abr_schema::Segment::PROGRESS) {
          update_segment(*segment);
        }
        break;
      case abr_schema::Segment::PROGRESS:
        if (last_segment.find(segment->index) == last_segment.end() || (
              last_segment[segment->index].state == abr_schema::Segment::PROGRESS &&
              last_segment[segment->index].timestamp < segment->timestamp)) {
          update_segment(*segment);
        }
        break;  
    }
  }
}

bool SegmentProgressAbr::should_send(int index) {
  if (index == 1) {
    return true;
  }

  if (last_segment.find(index - 1) == last_segment.end()) {
    // no stats from previous segment
    return false;
  }

  auto segment = last_segment[index - 1];
  if (segment.state != abr_schema::Segment::PROGRESS) {
    // segment has already been downloaded or loaded
    return true;
  }

  if (1.0 * segment.loaded / segment.total >= 0.8) {
    // segment has been downloaded more than 80%
    return true;
  }

  if (aborted.find(index - 1) != aborted.end()) {
    return true;
  }

  return false;
}

abr_schema::Decision SegmentProgressAbr::decide() { 
  int to_decide = decision_index;
  if (decisions.find(to_decide) == decisions.end() && should_send(to_decide)) {
    // decisions should be idempotent
    decisions[to_decide] = abr_schema::Decision(
      to_decide, 
      decideQuality(to_decide), 
      last_timestamp
    );
    decision_index += 1;

    QUIC_LOG(WARNING) << "[SegmentProgressAbr] new decision: [index] " << decisions[to_decide].index
                      << " [quality] " << decisions[to_decide].quality;
    return decisions[to_decide];
  } else {
    return decisions[to_decide - 1];
  }
}


RandomAbr::RandomAbr(const std::shared_ptr<DashBackendConfig>& config) 
  : SegmentProgressAbr(config) {}
RandomAbr::~RandomAbr() {}

int RandomAbr::decideQuality(int index) {
  int random_quality = rand() % segments.size();
  if (index == 1) {
    random_quality = 0;
  }
  return random_quality;
}


BBAbr::BBAbr(const std::shared_ptr<DashBackendConfig>& config) 
               : SegmentProgressAbr(config)
               , last_player_time(abr_schema::Value(0, 0)) 
               , last_buffer_level(abr_schema::Value(0, 0)) {} 
BBAbr::~BBAbr() {}

void BBAbr::registerMetrics(const abr_schema::Metrics &metrics) {
  SegmentProgressAbr::registerMetrics(metrics);
  for (auto const& player_time : metrics.playerTime) {
    if (player_time->timestamp > last_player_time.timestamp) {
      last_player_time = *player_time;
    }
  }
  
  for (auto const& buffer_level : metrics.bufferLevel) {
    if (buffer_level->timestamp > last_buffer_level.timestamp) {
      last_buffer_level = *buffer_level;
    }
  }
}

int BBAbr::decideQuality(int index) {
  double bitrate = 0;
  int quality = 0;
  int n = bitrate_array.size();
  
  if (index == 1) {
    return 0;
  }
 
  int buffer_level = last_buffer_level.value; 
  if (last_segment[index - 1].state == abr_schema::Segment::PROGRESS) { 
    int start_time = index > 2 ? last_segment[index - 2].timestamp : 0;
    int current_time = last_segment[index - 1].timestamp;

    double proportion = 1.0 * last_segment[index - 1].loaded / last_segment[index - 1].total;
    int download_time = 1.0 * (current_time - start_time) * (1 - proportion) / proportion;
    
    if (index < int(segments[0].size())) {
      last_segment_time_length = int(SECOND * (segments[0][index + 1].start_time - segments[0][index].start_time));
    }
    int bonus = last_segment_time_length - download_time; 
  
    buffer_level += bonus;  
  } 
  QUIC_LOG(WARNING) << " [last buffer level] " << buffer_level;

  if (buffer_level <= RESERVOIR) {
    bitrate = bitrate_array[0];
  } else if (buffer_level >= RESERVOIR + CUSHION) {
    bitrate = bitrate_array[n - 1];
  } else {
    bitrate = bitrate_array[0] + 1.0 * (bitrate_array[n - 1] - bitrate_array[0]) 
                                * (buffer_level - RESERVOIR) / CUSHION;
  }

  for (int i = n - 1; i >= 0; --i) {
    quality = i;
    if (bitrate >= bitrate_array[i]) {
      break;
    }
  }
  return quality;
}


}
