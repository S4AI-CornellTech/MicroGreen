Import("env")

for e in [env, DefaultEnvironment()]:
    e.Append(
        CCFLAGS=[
        "-mfloat-abi=hard",
        "-mfpu=fpv4-sp-d16",
        "-DARM_MATH_CM4=1"
        ],
        LINKFLAGS=[
        "-mfloat-abi=hard",
        "-mfpu=fpv4-sp-d16"
        ]
    )