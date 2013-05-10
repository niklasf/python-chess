#ifndef LIBCHESS_GAME_HEADER_BAG_H
#define LIBCHESS_GAME_HEADER_BAG_H

#include <string>
#include <unordered_map>

namespace chess {

class GameHeaderBag {
public:
    GameHeaderBag() { };
    std::string __getitem__(const std::string& key);
    void __setitem__(const std::string& key, const std::string& value);
    void __delitem__(const std::string& key);

private:
    std::unordered_map<std::string, std::string> m_map;
};

} // namespace chess

#endif // LIBCHESS_GAME_HEADER_BAG_H
