# Py2Cpp

A Python to C++ source code converter designed for competitive programming. \
\
**I built the core features myself, claude helped with comments, readme, and security fixes.**

<!-- Add your demo video here -->
https://github.com/user-attachments/assets/0c1d12af-e77f-4e1a-98db-8505fd204095

## Why Py2Cpp?

Python is great for prototyping solutions quickly, but often results in TLE (Time Limit Exceeded) on competitive programming judges. Py2Cpp lets you write readable Python code and convert it to C++ for faster execution times, without manually rewriting your solution.

## Features

- **CLI, API, and Web interfaces** - Use however you prefer
- **AST-based conversion** - Accurate translation of Python constructs to idiomatic C++
- **Type inference** - Automatically infers variable and function types
- **LLM fallback** - Falls back to Google Gemini for unsupported edge cases
- **LLM fix** - Fix C++ compilation errors using AI

## Installation

```bash
git clone https://github.com/Thomastienn/python2cpp.git
cd python2cpp
pip install -r requirements.txt
```

Requires Python 3.12+

## Usage

### CLI

```bash
python main.py input.py              # Outputs to input.cpp
python main.py input.py output.cpp   # Custom output file
python main.py input.py --debug      # Debug mode
python main.py input.py --quiet      # Suppress output
```

### API

Hosted at `https://python2cpp.onrender.com`

```bash
# Convert
curl -X POST https://python2cpp.onrender.com/convert \
  -H "Content-Type: application/json" \
  -d '{"pycode": "print(sum(range(10)))"}'

# Fix compilation errors
curl -X POST https://python2cpp.onrender.com/fix \
  -H "Content-Type: application/json" \
  -d '{"cppcode": "broken C++ code"}'
```

### Web Interface

Run locally:

```bash
cd webfrontend && npm install && npm run dev
```

## Supported Conversions

### Statements

| Python | C++ |
|--------|-----|
| `if`/`elif`/`else` | `if`/`else if`/`else` |
| `for i in range(n)` | `for (int i = 0; i < n; i++)` |
| `for x in arr` | `for (auto x : arr)` |
| `while` | `while` |
| `break`, `continue`, `pass` | `break`, `continue`, (omitted) |
| `return` | `return` |
| `a, b = 1, 2` | `auto [a, b] = make_tuple(1, 2)` |
| `a = b = 0` | `int a = 0; int b = 0;` |
| `a += 1` | `a += 1` |

### Operators

| Python | C++ |
|--------|-----|
| `+`, `-`, `*`, `/`, `//` | `+`, `-`, `*`, `/`, `/` |
| `**` | `fastpow()` template |
| `%` | `cmod()` template (handles negatives) |
| `<<`, `>>`, `\|`, `&`, `^`, `~` | Same |
| `and`, `or`, `not` | `&&`, `\|\|`, `!` |
| `==`, `!=`, `<`, `<=`, `>`, `>=` | Same |
| `x if cond else y` | `(cond) ? (x) : (y)` |
| `x in list` | `find(v.begin(), v.end(), x) != v.end()` |
| `x in set` | `s.count(x) > 0` |
| `x in string` | `s.find(x) != npos` |

### Data Types

| Python | C++ |
|--------|-----|
| `int`, `float`, `bool`, `str` | `int`, `float`, `bool`, `string` |
| `list` | `vector<T>` |
| `tuple` | `tuple<...>` |
| `dict` | `map<K, V>` |
| `set` | `set<T>` |
| `[0] * n` | `vector<T>(n, 0)` |
| `[1, 2, 3]` | `vector{1, 2, 3}` |
| `{k: v}` | `map<K, V>{{k, v}}` |

### Built-in Functions

| Python | C++ |
|--------|-----|
| `print()` | `cout << ... << "\n"` |
| `input()` | `cinput()` template |
| `len()` | `.size()` |
| `range(n)`, `range(a, b)`, `range(a, b, step)` | C-style for loop |
| `int()`, `float()`, `str()`, `bool()` | Type casts / `stoi()`, `to_string()` |
| `ord()`, `chr()` | `static_cast<int/char>()` |
| `min()`, `max()` | `min()`, `max()` |
| `map(func, iter)` | Inline loop or `cmap()` template |
| `reversed()` | `rbegin()`/`rend()` or `crev()` template |

### Methods

| Python | C++ |
|--------|-----|
| `.append()` | `.push_back()` |
| `.sort()` | `sort(v.begin(), v.end())` |
| `.split()` | `csplit()` template |

### Slicing

| Python | C++ |
|--------|-----|
| `arr[i]` | `arr[i]` |
| `arr[-1]` | `arr[arr.size() - 1]` |
| `s[a:b]` (string) | `s.substr(a, b-a)` |
| `v[a:b]` (vector) | `vector<T>(v.begin()+a, v.begin()+b)` |
| `arr[a:b:step]` | `cslice()` template |

### List Comprehensions

```python
[x*2 for x in range(n)]
[[0 for j in range(m)] for i in range(n)]
```

Converts to lambda expressions with vector construction.

### Tuple Unpacking

```python
a, b = 1, 2           # -> auto [a, b] = make_tuple(1, 2)
a, b = func()         # -> auto [a, b] = func()
n, m = map(int, ...)  # -> auto [n, m] = ...
```

## C++ Templates

The converter includes helper templates for Python-like behavior:

| Template | Purpose |
|----------|---------|
| `fastpow(a, b)` | O(log n) exponentiation |
| `cmod(a, b)` | Python-style modulo (handles negatives) |
| `cinput(prompt)` | Input with optional prompt |
| `csplit(s, delim)` | String splitting |
| `cmap(func, iter)` | Map function |
| `crev(container)` | Reverse container |
| `cslice(arr, a, b, step)` | Slice with step |

## Example

### Python Input

```python
mod = 10**9+7

def multiply(a, b):
    res = [[0 for j in range(len(b[0]))] for i in range(len(a))]
    for i in range(len(a)):
        for j in range(len(b[0])):
            for k in range(len(b)):
                res[i][j] = (res[i][j] + a[i][k] * b[k][j]) % mod
    return res

n, m = map(int, input().split())
print(n + m)
```

### C++ Output

```cpp
#include <bits/stdc++.h>
using namespace std;

int mod;

// Helper templates (csplit, fastpow, cmod, etc.)
// ...

vector<vector<int>> multiply(vector<vector<int>> a, vector<vector<int>> b) {
    vector<vector<int>> res = [&] {
        vector<vector<int>> parent;
        for (int i = 0; i < a.size(); i += 1) {
            vector<int> temp = [&] {
                vector<int> parent;
                for (int j = 0; j < b[0].size(); j += 1) {
                    parent.push_back(0);
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

int main() {
    mod = (fastpow(10, 9) + 7);
    auto [n, m] = [&] {
        vector<int> temp;
        vector<string> parts = csplit(cinput());
        for (int i = 0; i < parts.size(); i++) {
            temp.push_back(stoi(parts[i]));
        }
        return make_tuple(temp[0], temp[1]);
    }();
    cout << (n + m) << "\n";
    return 0;
}
```

## Self-Hosting

### Backend

```bash
cd webbackend
pip install -r requirements.txt
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

With Docker:

```bash
cd webbackend
docker build -t py2cpp-backend .
docker run -p 8000:8000 py2cpp-backend
```

### Frontend

```bash
cd webfrontend
npm install && npm run build
npm run deploy  # GitHub Pages
```

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/convert` | POST | Convert Python to C++ |
| `/fix` | POST | Fix C++ compilation errors |

**Request body:** `{"pycode": "..."}` or `{"cppcode": "..."}`

## Limits

- 30 requests/min per IP
- Max input: 30KB
- Max AST nodes: 1000

## Project Structure

```
python2cpp/
├── main.py              # CLI entry point
├── py2c/
│   ├── commands/        # CLI, parser, LLM fallback
│   ├── core/            # AST processor, visitor, structures
│   └── utils/           # Templates, typeinferencer, constants
├── webbackend/          # FastAPI server
└── webfrontend/         # React + Vite + Monaco
```

## License

MIT
