# Py2Cpp

- A simple python to C++ converter
- CLI, API, Web supported
- In development (expect LOTS OF bugs)

### Note

- I assume the python code was runnable without runtime or syntax error
- It has not yet support for libraries (only vanilla python)
- It cannot copy comments to cpp yet (low priority)
- It can still produce syntax error (use with caution)
- It will not produce unused functions ()

### DEMO

#### Python

```python
mod = 10**9+7
def multiply(a, b):
    res = [[0 for j in range(len(b[0]))] for i in range(len(a))]
    for i in range(len(a)):
        for j in range(len(b[0])):
            for k in range(len(b)):
                res[i][j] = (res[i][j] + a[i][k] * b[k][j])%mod
    return res

def power(x, n):
    res = [[1 if j == i else 0 for j in range(len(x))] for i in range(len(x))]
    while n:
        if n&1:
            res = multiply(res, x)
        x = multiply(x, x)
        n >>= 1
    return res

n,m,t = map(int, input().split())

A = [[1 if i == j else 0 for i in range(n+1)] for j in range(n+1)]
types = [int(input()) for _ in range(n)]

for i in range(m):
    u,v = map(int, input().split())
    if types[v] == 1:
        A[u][-1] += 1
    else:
        A[u][v] += 1
    if types[u] == 1:
        A[v][-1] += 1
    else:
        A[v][u] += 1


A = power(A, t)
A = multiply(A, [[1] for _ in range(n+1)])

ans = 0
for i in range(n):
    ans += A[i][0]
print(ans)
```

#### C++

```cpp
#include <bits/stdc++.h>
using namespace std;

// All the variables I assume you want to be global
int mod;

// Just my templates to replace python functions
vector<string> csplit(const string& s, const string& delim = " ") {
    vector<string> result;
    size_t start = 0, end;

    while ((end = s.find(delim, start)) != string::npos) {
        result.push_back(s.substr(start, end - start));
        start = end + delim.length();
    }
    result.push_back(s.substr(start));
    return result;
}

string cinput(string prompt = "") {
    cout << prompt;
    string s;
    getline(cin, s);
    return s;
}

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
}

int cmod(int a, int b) {
    return (a % b + b) % b;
}


// Your functions are here
vector<vector<int>> multiply(vector<vector<int>> a, vector<vector<int>> b) {
    vector<vector<int>> res = [&] {
        vector<vector<int>> parent;
        for (int i = 0; i < a.size(); i += 1) {
            vector<int> temp = [&] {
                vector<int> parent;
                for (int j = 0; j < b[0].size(); j += 1) {
                    int temp = 0;
                    parent.push_back(temp);
                }
                return parent;
            }();
            parent.push_back(temp);
        }
        return parent;
    }();
    for (int i = 0; i < a.size(); i += 1) {
        for (int j = 0; j < b[0].size(); j += 1) {
            for (int k = 0; k < b.size(); k += 1) {
                res[i][j] = cmod((res[i][j] + (a[i][k] * b[k][j])), mod);
            }
        }
    }
    return res;
}
vector<vector<int>> power(vector<vector<int>> x, int n) {
    vector<vector<int>> res = [&] {
        vector<vector<int>> parent;
        for (int i = 0; i < x.size(); i += 1) {
            vector<int> temp = [&] {
                vector<int> parent;
                for (int j = 0; j < x.size(); j += 1) {
                    int temp = (j == i)? (1) : (0);
                    parent.push_back(temp);
                }
                return parent;
            }();
            parent.push_back(temp);
        }
        return parent;
    }();
    while (n) {
        if ((n & 1)) {
            res = multiply(res, x);
        }
        x = multiply(x, x);
        n >>= 1;
    }
    return res;
}

int main() {
    mod = (fastpow(10, 9) + 7);
    auto [n,m,t] = [&] {
        vector<int>temp;
        vector<string> arg2 = csplit(cinput());
        for (int i = 0; i < arg2.size(); i++){
            temp.push_back(stoi(arg2[i]));
        }
        return make_tuple(temp[0], temp[1], temp[2]);
    }();
    vector<vector<int>> A = [&] {
        vector<vector<int>> parent;
        for (int j = 0; j < (n + 1); j += 1) {
            vector<int> temp = [&] {
                vector<int> parent;
                for (int i = 0; i < (n + 1); i += 1) {
                    int temp = (i == j)? (1) : (0);
                    parent.push_back(temp);
                }
                return parent;
            }();
            parent.push_back(temp);
        }
        return parent;
    }();
    vector<int> types = [&] {
        vector<int> parent;
        for (int _ = 0; _ < n; _ += 1) {
            int temp = stoi(cinput());
            parent.push_back(temp);
        }
        return parent;
    }();
    for (int i = 0; i < m; i += 1) {
        auto [u,v] = [&] {
            vector<int>temp;
            vector<string> arg2 = csplit(cinput());
            for (int i = 0; i < arg2.size(); i++){
                temp.push_back(stoi(arg2[i]));
            }
            return make_tuple(temp[0], temp[1]);
        }();
        if (types[v] == 1) {
            A[u][A[u].size() - 1] += 1;
        }
        else {
            A[u][v] += 1;
        }
        if (types[u] == 1) {
            A[v][A[v].size() - 1] += 1;
        }
        else {
            A[v][u] += 1;
        }
    }
    A = power(A, t);
    A = multiply(A, [&] {
        vector<vector<int>> parent;
        for (int _ = 0; _ < (n + 1); _ += 1) {
            vector<int> temp = vector{1};
            parent.push_back(temp);
        }
        return parent;
    }());
    int ans = 0;
    for (int i = 0; i < n; i += 1) {
        ans += A[i][0];
    }
    cout << ans << "\n";
    return 0;
}
```
