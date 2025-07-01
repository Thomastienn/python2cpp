k, m = map(int, input().split())
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
    
print(ans)
