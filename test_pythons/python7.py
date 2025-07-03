cache = [-1] * 1000
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
print(fib(6))
