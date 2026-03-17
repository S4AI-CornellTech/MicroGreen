#ifndef MODEL_CONFIG_H_
#define MODEL_CONFIG_H_

#include "tensorflow/lite/micro/micro_mutable_op_resolver.h"
#include <cstdint>

#include "kws_model_data.h"
#include "kws_model_settings.h"

namespace ModelConfig
{
    inline const unsigned char *GetModelData()
    {
        return g_kws_model_data;
    }

    constexpr int kTensorArenaSize = 28584;

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
        return "KWS Small";
    }

    template <unsigned int N>
    inline void InitializeOpResolver(tflite::MicroMutableOpResolver<N> &resolver)
    {
        resolver.AddReshape();
        resolver.AddFullyConnected();
        resolver.AddDepthwiseConv2D();
        resolver.AddSoftmax();
    }

    // Number of operations needed (for template parameter)
    constexpr int kOpResolverSize = 4;

}

alignas(16) inline uint8_t tensor_arena[ModelConfig::kTensorArenaSize];

#endif