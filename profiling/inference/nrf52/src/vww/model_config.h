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
    constexpr int kTensorArenaSize = 124 * 1024;

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
        resolver.AddAveragePool2D();
        resolver.AddConv2D();
        resolver.AddDepthwiseConv2D();
        resolver.AddReshape();
        resolver.AddSoftmax();
        resolver.AddFullyConnected();
    }

    constexpr int kOpResolverSize = 6;
}

// alignas(16) inline uint8_t tensor_arena[ModelConfig::kTensorArenaSize];

#endif                                                                                                                                                                  