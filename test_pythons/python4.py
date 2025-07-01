# Count character frequencies and find most frequent character

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
print("Frequency:", count)

