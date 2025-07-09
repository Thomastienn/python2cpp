export interface Preset {
    name: string;
    code: string;
}

export const pythonPresets: Preset[] = [
    {
        name: 'Matrix Power (python.py)',
        code: `mod = 10**9+7
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
print(ans)`,
    },
    {
        name: 'Fibonacci Matrix (python1.py)',
        code: `a = [[1, 2], [3, 4]]
b = [[0, 1], [0, 1]]
mod = 10**9
def multiply(a, b):
    res = [[0, 0], [0, 0]]
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

def fibo(n):
    base = [[1, 1], [1, 0]]
    # 1 1 f(n) f(n+1)
    # 1 0 f(n-1) f(n)
    
    res = power(base, n-1)
    
    return res[0][1]
    
n = int(input())
for _ in range(n):
    i, num = map(int, input().split())
    print(i, fibo(num))`,
    },
    {
        name: 'Segment Tree (python2.py)',
        code: `n, q = map(int, input().split())
a = list(map(int, input().split()))

def push(node):
    tree[2*node] += lazy[node]
    lazy[2*node] += lazy[node]
    tree[2*node+1] += lazy[node]
    lazy[2*node+1] += lazy[node]
    lazy[node] = 0

def find_sum(node, node_low, node_high, low, high):
    if low <= node_low and node_high <= high:
        return tree[node]
    if node_high < low or node_low > high:
        return 0
    push(node)
    mid_left = (node_low + node_high)//2
    return find_sum(2*node, node_low, mid_left, low, high) \
            + find_sum(2*node + 1, mid_left+1, node_high, low, high)

def updateRange(node, node_low, node_high, low, high, value):
    if low > high:
        return
    if node_low == low and node_high == high:
        tree[node] = value
        lazy[node] += value
    else:
        push(node)
        node_mid = (node_low+node_high)//2
        updateRange(2*node, node_low, node_mid, low, min(high, node_mid), value)
        updateRange(2*node+1, node_mid+1, node_high, max(low, node_mid+1), high, value)
        tree[node] = tree[node*2] + tree[node*2+1]

def updateIterative(node, value, n):
    tree[n+node] = value
    j = (n+node)//2 # Parent of this node
    while j >= 1:
        tree[j] = tree[2*j] + tree[2*j+1]
        j /= 2
def updateRecursive(node, node_low, node_high, low, high, value):
    if low <= node_low and node_high <= high:
        tree[node] = value
        return
    if node_high < low or node_low > high:
        return
    mid_left = (node_low + node_high)//2
    updateRecursive(2*node, node_low, mid_left, low, high, value)
    updateRecursive(2*node+1, mid_left+1, node_high, low, high, value)
    
    tree[node] = tree[2*node] + tree[2*node+1]
    
k = (1 << n.bit_length())
tree = [0] * (2 * k)
lazy = [0] * (2 * k)
# Leaf nodes
for i in range(n):
    tree[k+i] = a[i]
# Build upper nodes
for i in range(k-1, 0, -1):
    tree[i] = tree[2*i] + tree[2*i+1]

for _ in range(q):
    s, e = map(int, input().split())
    s -= 1
    e -= 1
    
    print(find_sum(1, 0, k-1, s, e))
    
updateRange(1, 0, k-1, 0, 1, 3)
print(find_sum(1, 0, k-1, 1, 3))`,
    },
    {
        name: 'Fibonacci Iterative (python3.py)',
        code: `def fib(n):
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    else:
        a, b = 0, 1
        for _ in range(2, n + 1):
            a, b = b, a + b
        return b
print(fib(10))`,
    },
    {
        name: 'Character Frequency (python4.py)',
        code: `# Count character frequencies and find most frequent character

def count_char_freq(s):
    freq = [0] * 128  # ASCII size

    i = 0
    while i < len(s):
        ch = s[i]
        ascii_val = ord(ch)
        if ascii_val < 128:
            freq[ascii_val] = freq[ascii_val] + 1
        i = i + 1

    # Find the most frequent character
    max_freq = 0
    max_char = ''
    i = 0
    while i < 128:
        if freq[i] > max_freq:
            max_freq = freq[i]
            max_char = chr(i)
        i = i + 1

    return max_char, max_freq

# Test input
text = "hello world! look at me goooo"

char, count = count_char_freq(text)

print("Most frequent character:", char)
print("Frequency:", count)`,
    },
    {
        name: 'Brick Cost (python5.py)',
        code: `k, m = map(int, input().split())
c = list(map(int, input().split()))

ans = float("inf")
for brick in range(1,k+1):
    cost = 0
    cur_bricks = 0
    for i in range(m):
        if cur_bricks >= k:
            break
        cost += c[i]*brick
        cur_bricks += brick
    if cur_bricks >= k:
        ans = min(ans, cost)
    
print(ans)`,
    },
    {
        name: 'Fibonacci Recursive (python6.py)',
        code: `def fib(n):
    result = -1
    if n == 1 or n == 2:
        result = 1
    else:
        result = fib(n-1) + fib(n-2)
    return result

fib(3)`,
    },
    {
        name: 'Fibonacci Memoized (python7.py)',
        code: `cache = [-1] * 1000
def fib(n):
    if cache[n] != 0-1:
        return cache[n]
    result = 0
    if n == 1 or n == 2: 
        result = 1
    else:
        result = fib(n-1) + fib(n-2)
    cache[n] = result
    return result
print(fib(6))`,
    },
];
