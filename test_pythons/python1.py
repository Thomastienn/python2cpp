a = [[1, 2], [3, 4]]
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
    print(i, fibo(num))

