/* Copyright 2023 The TensorFlow Authors. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
==============================================================================*/

#ifndef TENSORFLOW_LITE_MICRO_EXAMPLES_MICRO_SPEECH_MICRO_MODEL_SETTINGS_H_
#define TENSORFLOW_LITE_MICRO_EXAMPLES_MICRO_SPEECH_MICRO_MODEL_SETTINGS_H_

// The following values are derived from values used during model training.
// If you change the way you preprocess the input, update all these constants.


constexpr int kFeatureSize = 40;
constexpr int kFeatureCount = 49;

constexpr int kNumCols = kFeatureSize;    // 40 - frequency dimension
constexpr int kNumRows = kFeatureCount;   // 49 - time dimension  
constexpr int kNumChannels = 1;           // Single channel audio

// Input size calculation - both ways for compatibility
constexpr int kKwsInputSize = kNumCols * kNumRows * kNumChannels;  // Standard name

// Variables for the model's output categories.
constexpr int kCategoryCount = 4;
extern const char* kCategoryLabels[kCategoryCount];

#endif  // TENSORFLOW_LITE_MICRO_EXAMPLES_MICRO_SPEECH_MICRO_MODEL_SETTINGS_H_