#ifndef LIBCHESS_ATTACKER_GENERATOR_H
#define LIBCHESS_ATTACKER_GENERATOR_H

#include "position.h"

namespace chess {

   class Position;

   /**
    * \brief Enumerates attackers of a given side on a specific square of the
    *   given position.
    */
   class AttackerGenerator : boost::noncopyable {
   public:
       AttackerGenerator(const Position& position, char color, Square target);

       int __len__();
       bool __nonzero__();
       AttackerGenerator& __iter__();
       bool __contains__(Square square);

       bool has_more();
       Square next();
       Square python_next();

   private:
       char m_color;
       const Position& m_position;
       Square m_target;
       int m_source_index;
   };

}

#endif
