def find_max(nums):
    best = nums[0]
    for n in nums:
        if n > best:
            best = n
    return best
