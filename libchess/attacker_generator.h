#ifndef LIBCHESS_ATTACKER_GENERATOR_H
#define LIBCHESS_ATTACKER_GENERATOR_H

#include "position.h"

namespace chess {

   class AttackerGenerator {
   public:
       AttackerGenerator(Position position, char color, Square target);

       int __len__();
       bool __nonzero__();
       AttackerGenerator __iter__();
       bool __contains__(Square square);
       Square next();

   private:
       char m_color;
       Position m_position;
       Square m_target;
       int m_source_index;
   };

}

#endif
