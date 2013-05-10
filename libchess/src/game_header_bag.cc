#include "game_header_bag.h"

namespace chess {

std::string GameHeaderBag::__getitem__(const std::string& key) {
    return m_map[key];
}

void GameHeaderBag::__setitem__(const std::string& key, const std::string& value) {
    m_map[key] = value;
}

void GameHeaderBag::__delitem__(const std::string& key) {
    m_map.erase(key);
}

} // namespace chess
