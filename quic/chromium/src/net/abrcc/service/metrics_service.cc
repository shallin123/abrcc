#include "net/abrcc/service/metrics_service.h"
#include "net/abrcc/service/schema.h"

#include "net/third_party/quiche/src/quic/platform/api/quic_logging.h"
#include "net/third_party/quiche/src/quic/platform/api/quic_text_utils.h"
#include "net/third_party/quiche/src/quic/platform/api/quic_mutex.h"

#include "base/json/json_value_converter.h"
#include "base/json/json_reader.h"
#include "base/json/json_writer.h"
#include "base/values.h"

using namespace abr_schema;
using spdy::SpdyHeaderBlock;

namespace quic {

MetricsService::MetricsService() {}
MetricsService::~MetricsService() {}

void MetricsService::AddMetrics(
  const SpdyHeaderBlock& request_headers,
  const std::string& data, 
  QuicSimpleServerBackend::RequestHandler* quic_stream
) {
  DashRequest* request(new DashRequest());
   
  base::Optional<base::Value> value = base::JSONReader::Read(data);
  base::JSONValueConverter<DashRequest> converter;
  converter.Convert(*value, request);
  
  AddMetricsImpl(&request->metrics);
}

void MetricsService::AddMetricsImpl(Metrics* metrics) {
  QuicWriterMutexLock lock(&mutex_);

  std::unique_ptr<Metrics> to_push(metrics);
  this->metrics.push_back(std::move(to_push)); 
}
  
std::vector<std::unique_ptr<Metrics>> MetricsService::GetMetrics() {
  QuicWriterMutexLock lock(&mutex_);
  
  std::vector<std::unique_ptr<Metrics>> out = std::move(metrics);
  metrics = std::vector<std::unique_ptr<Metrics>>();
  return out;
}

void MetricsService::AddAbort(int abort_index) {
  QuicWriterMutexLock lock(&mutex_);
  this->aborts.push_back(abort_index);
}

std::vector<int> MetricsService::GetAborts() {
  QuicWriterMutexLock lock(&mutex_);

  std::vector<int> out = std::move(aborts);
  aborts = std::vector<int>();
  return out;
}

}
