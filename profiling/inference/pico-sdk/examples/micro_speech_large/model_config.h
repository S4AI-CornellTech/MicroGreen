#ifndef MODEL_CONFIG_H_
#define MODEL_CONFIG_H_

#include "tensorflow/lite/micro/micro_mutable_op_resolver.h"
#include <cstdint>

// Model-specific includes - change these when switching models
#include "kws_model_data.h"
#include "kws_model_settings.h"

// Model configuration
namespace ModelConfig
{
    // Model data pointer
    inline const unsigned char *GetModelData()
    {
        return g_kws_model_data;
    }

    // Model-specific tensor arena size
    constexpr int kTensorArenaSize = 32 * 1024; // 32KB for KWS large model

    // Input dimensions (from model settings)
    constexpr int GetInputSize()
    {
        return kKwsInputSize;
    }

    // Number of output categories
    constexpr int GetCategoryCount()
    {
        return kCategoryCount;
    }

    // Get category labels
    inline const char **GetCategoryLabels()
    {
        return kCategoryLabels;
    }

    // Model name for logging
    constexpr const char *GetModelName()
    {
        return "KWS Large";
    }

    // Initialize the op resolver with required operations
    template <unsigned int N>
    inline void InitializeOpResolver(tflite::MicroMutableOpResolver<N> &resolver)
    {
        resolver.AddFullyConnected();
        resolver.AddConv2D();
        resolver.AddDepthwiseConv2D();
        resolver.AddReshape();
        resolver.AddSoftmax();
        resolver.AddAveragePool2D();
    }

    // Number of operations needed (for template parameter)
    constexpr int kOpResolverSize = 6;
}

// Global tensor arena - defined here since we only include this in main.cpp
// If you include this header in multiple .cpp files, move this to a .cc file
alignas(16) inline uint8_t tensor_arena[ModelConfig::kTensorArenaSize];

#endif // MODEL_CONFIG_H_