n, q = map(int, input().split())
a = list(map(int, input().split()))

#IMPORTANT
# 2*i : left node
# 2*i + 1: right node
# i//2 : Parent node
# index 1 is the root (not 0)

# Test case
# 5 3
# 1 3 5 7 9
# 1 3
# 2 4
# 0 4

# Expected
# 9
# 15
# 16

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
print(find_sum(1, 0, k-1, 1, 3))

