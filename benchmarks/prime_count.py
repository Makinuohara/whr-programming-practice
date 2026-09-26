"""Trial-division prime counting benchmark equivalent to prime_count.whr."""


LIMIT = 3000


def is_prime(number):
    if number < 2:
        return False
    divisor = 2
    while divisor * divisor <= number:
        if number % divisor == 0:
            return False
        divisor = divisor + 1
    return True


def count_primes(bound):
    count = 0
    candidate = 2
    while candidate <= bound:
        if is_prime(candidate):
            count = count + 1
        candidate = candidate + 1
    return count


print("prime_count:", count_primes(LIMIT))
