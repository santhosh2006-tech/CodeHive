def add(a, b):
    """
    Add two numbers.
    
    Args:
        a (float): The first number.
        b (float): The second number.
    
    Returns:
        float: The sum of a and b.
    """
    return a + b


def subtract(a, b):
    """
    Subtract two numbers.
    
    Args:
        a (float): The first number.
        b (float): The second number.
    
    Returns:
        float: The difference of a and b.
    """
    return a - b


def multiply(a, b):
    """
    Multiply two numbers.
    
    Args:
        a (float): The first number.
        b (float): The second number.
    
    Returns:
        float: The product of a and b.
    """
    return a * b


def divide(a, b):
    """
    Divide two numbers.
    
    Args:
        a (float): The first number.
        b (float): The second number.
    
    Returns:
        float: The quotient of a and b.
    
    Raises:
        ZeroDivisionError: If b is zero.
    """
    if b == 0:
        raise ZeroDivisionError("Cannot divide by zero")
    return a / b