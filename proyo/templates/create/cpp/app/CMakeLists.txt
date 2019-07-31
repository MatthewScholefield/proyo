# ~ if build_system == 'cmake':

project({{project_name}})

set(CMAKE_CXX_STANDARD {{cxx_standard}})

add_executable(
        musidy_app
        source/main.cpp
)

# ~ #