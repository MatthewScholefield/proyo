# ~ if build_system == 'cmake':

project({{project_name}})

set(CMAKE_CXX_STANDARD {{cxx_standard}})

add_executable(
        {{project_name}}
        source/main.cpp
)

# ~ #
