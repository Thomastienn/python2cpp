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
