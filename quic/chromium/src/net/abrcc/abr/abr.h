#ifndef ABRCC_ABR_ABR_H_
#define ABRCC_ABR_ABR_H_

#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wc++17-extensions"

#include "net/abrcc/abr/interface.h"
#include "net/abrcc/cc/bbr_adapter.h"
#include "net/abrcc/service/schema.h"

#include <unordered_map>

namespace quic {

class SegmentProgressAbr : public AbrInterface {
 public:
  SegmentProgressAbr();
  ~SegmentProgressAbr() override;

  void registerMetrics(const abr_schema::Metrics &) override;
  abr_schema::Decision decide() override;

  virtual int decideQuality(int index) = 0; 
 protected:
  std::unordered_map<int, abr_schema::Segment> last_segment;  
  std::unordered_map<int, abr_schema::Decision> decisions; 
  int decision_index;
  int last_timestamp;
 private:
  void update_segment(abr_schema::Segment segment);
  bool should_send(int index);
};

class RandomAbr : public SegmentProgressAbr {
 public: 
  RandomAbr();
  ~RandomAbr() override;

 int decideQuality(int index) override;
};

class BBAbr : public SegmentProgressAbr {
 public:
  BBAbr();
  ~BBAbr() override;

  void registerMetrics(const abr_schema::Metrics &) override;
  int decideQuality(int index) override;
 private:
  abr_schema::Value last_player_time;
  abr_schema::Value last_buffer_level;
};

class WorthedAbr : public SegmentProgressAbr {
 public:
  WorthedAbr();
  ~WorthedAbr() override;

  void registerMetrics(const abr_schema::Metrics &) override;
  int decideQuality(int index) override;
 private:
  int adjustedBufferLevel(int index);
  
  std::pair<int, int> computeRates(bool stochastic);
  void adjustCC(); 
  void setRttProbing(bool probing);

  BbrAdapter::BbrInterface* interface; 

  bool is_rtt_probing;

  abr_schema::Value last_player_time;
  abr_schema::Value last_buffer_level;
  
  base::Optional<abr_schema::Value> last_bandwidth;
  base::Optional<abr_schema::Value> last_rtt;
};

AbrInterface* getAbr(const std::string& abr_type);

}

#pragma GCC diagnostic pop

#endif
