from enum import Enum
import textwrap

class CPPTemplate(Enum):
    FASTPOW = textwrap.dedent("""
    template<typename T>
    T fastpow(T a, T b) {
        T res = 1;
        while (b > 0) {
            if (b & 1) {
                res *= a;
            }
            a *= a;
            b >>= 1;
        }
        return res;
    }
    """)

    MODPOW = textwrap.dedent("""
    template<typename T>
    T modpow(T a, T b, T mod) {
        T res = 1;
        while (b > 0) {
            if (b & 1) {
                res = (res * a) % mod;
            }
            a = (a * a) % mod;
            b >>= 1;
        }
        return res;
    }
    """)

    ENUMERATE_CPP = textwrap.dedent("""
    template <ranges::input_range R>
    auto enumerate_cpp(R&& range) {
        size_t index = 0;
        return views::transform(forward<R>(range), 
            [&index](auto&& elem) mutable {
                return pair{index++, elem};
            });
    }
    """)

    CINPUT = textwrap.dedent("""
    string cinput() {
        string s;
        getline(cin, s);
        return s;
    }
    """)


    
