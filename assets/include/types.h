// this file was manually generated for now, because I figured it wouldn't change much between 
// versions

#ifndef TYPES__H
#define TYPES__H

#include <cstddef>
#include <cstdint>

namespace gl {
   // TODO: should we be using KHR for this stuff?

   using enum_t = unsigned int;
   using bitfield_t = unsigned int;
   using byte_t = std::int8_t;
   using short_t = short;
   using int_t = int;
   using int64_t = std::int64_t;
   using fixed_t = std::int32_t;
   using ubyte_t = std::uint8_t;
   using ushort_t = unsigned short;
   using uint_t = unsigned int;
   using uint64_t = std::uint64_t;
   using sizei_t = int;
   using float_t = float;
   using clampf_t = float;
   using double_t = double;
   using char_t = char;

   using sizeiptr_t = std::ptrdiff_t;
   using intptr_t = std::ptrdiff_t;
}

#endif // #ifndef TYPES__H
