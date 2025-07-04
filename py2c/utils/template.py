from enum import Enum
import textwrap

# This is in python type
class CPPTemplateReturnType(Enum):
    FASTPOW = "int"
    MODPOW = "int"
    ENUMERATE_CPP = "auto"
    CINPUT = "str"
    CSPLIT = ["list", "str"]
    CMAP = "auto"
    CMOD = "int"
    CREV = "auto"
    OVERLOAD_VECTOR_PRINT = "auto"

class CPPTemplate(Enum):
    FASTPOW = textwrap.dedent("""
    template <typename T>
    long long fastpow(T a, T b) {
        long long res = 1;
        while (b > 0) {
            if (b & 1) {
                res *= a;
            }
            a *= a;
            b >>= 1;
        }
        return res;
    }""")

    MODPOW = textwrap.dedent("""
    template <typename T>
    int modpow(T a, T b, T mod) {
        T res = 1;
        while (b > 0) {
            if (b & 1) {
                res = (res * a) % mod;
            }
            a = (a * a) % mod;
            b >>= 1;
        }
        return res;
    }""")

    ENUMERATE_CPP = textwrap.dedent("""
    template <ranges::input_range R>
    auto enumerate_cpp(R&& range) {
        size_t index = 0;
        return views::transform(forward<R>(range), 
            [&index](auto&& elem) mutable {
                return pair{index++, elem};
            });
    }""")

    CINPUT = textwrap.dedent("""
    string cinput(string prompt = "") {
        cout << prompt;
        string s;
        getline(cin, s);
        return s;
    }""")

    CSPLIT = textwrap.dedent("""
    vector<string> csplit(const string& s, const string& delim = " ") {
        vector<string> result;
        size_t start = 0, end;

        while ((end = s.find(delim, start)) != string::npos) {
            result.push_back(s.substr(start, end - start));
            start = end + delim.length();
        }
        result.push_back(s.substr(start));
        return result;
    }""")

    CMAP = textwrap.dedent("""
    template <typename Func, typename T>
    vector<decltype(declval<Func>()(declval<T>()))> cmap(Func f, const vector<T>& vec) {
        using ReturnType = decltype(f(vec[0]));
        vector<ReturnType> result;
        result.reserve(vec.size());

        for (const auto& item : vec) {
            result.push_back(f(item));
        }

        return result;
    }
    """)

    CMOD = textwrap.dedent("""
    template <typename T>
    int cmod(int a, int b) {
        return (a % b + b) % b;
    }
    """)

    CREV = textwrap.dedent("""
    template <typename T>
    T crev(const T& a) {
        return T(a.rbegin(), a.rend());
    }
    """)

    OVERLOAD_VECTOR_PRINT = textwrap.dedent("""
    template <typename T>
    ostream& operator<<(ostream& os, const vector<T>& v) {
        for (const auto& elem : v) {
            os << elem << " ";
        }
        return os;
    }
    """)  



    
