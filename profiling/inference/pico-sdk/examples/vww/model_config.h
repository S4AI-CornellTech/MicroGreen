#ifndef MODEL_CONFIG_H_
#define MODEL_CONFIG_H_


#include "tensorflow/lite/micro/micro_mutable_op_resolver.h"
#include <cstdint>

#include "./vww_model_data.h"
#include "./vww_model_settings.h"

namespace ModelConfig
{
    inline const unsigned char *GetModelData()
    {
        return g_person_detect_model_data;
    }
    constexpr int kTensorArenaSize = 200 * 1024;

    constexpr int GetInputSize()
    {
        return kKwsInputSize;
    }
    constexpr int GetCategoryCount()
    {
        return kCategoryCount;
    }

    inline const char **GetCategoryLabels()
    {
        return kCategoryLabels;
    }

    constexpr const char *GetModelName()
    {
        return "Visual Wake Word";
    }

    template <unsigned int N>
    inline void InitializeOpResolver(tflite::MicroMutableOpResolver<N> &resolver)
    {
        resolver.AddAveragePool2D(tflite::Register_AVERAGE_POOL_2D_INT8());
        resolver.AddConv2D(tflite::Register_CONV_2D_INT8());
        resolver.AddDepthwiseConv2D(tflite::Register_DEPTHWISE_CONV_2D_INT8());
        resolver.AddReshape();
        resolver.AddSoftmax(tflite::Register_SOFTMAX_INT8());
        resolver.AddFullyConnected(tflite::Register_FULLY_CONNECTED_INT8());
    }

    constexpr int kOpResolverSize = 6;
}

alignas(16) inline uint8_t tensor_arena[ModelConfig::kTensorArenaSize];

#endif