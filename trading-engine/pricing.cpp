#include <iomanip>
#include <iostream>

int main(int argc, char* argv[]) {
    if (argc < 2) return 1;
    double price = std::stod(argv[1]);
    double bid = price - 0.05;
    double ask = price + 0.05;
    double option = price * 0.025;
    std::cout << std::fixed << std::setprecision(2) << bid << " " << ask << " " << option << "\n";
    return 0;
}
