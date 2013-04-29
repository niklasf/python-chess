#ifndef LIBCHESS_ATTACKER_GENERATOR_H
#define LIBCHESS_ATTACKER_GENERATOR_H

#include "position.h"

namespace chess {

   class Position;

   class AttackerGenerator {
   public:
       AttackerGenerator(const Position& position, char color, Square target);

       int __len__();
       bool __nonzero__();
       AttackerGenerator __iter__();
       bool __contains__(Square square);
       Square python_next();

   private:
       char m_color;
       const Position& m_position;
       Square m_target;
       int m_source_index;
   };

}

#endif
