
import numpy as np


class Rectangle():
    
    def __init__(self, a, b):
        self._a = a
        self._b = b
        self.calc_area()
    
    def __repr__(self):
        return "Rectangle with a = {} and b = {}.".format(self._a, self._b)
        
    def calc_area(self):
        self.area = self._a * self._b
        return self.area
    
    def calc_perimeter(self):
        return 2 * self._a + 2 * self._b
    
    def calc_diagonal(self):
        return np.sqrt(self._a**2 + self._b ** 2)  
    
    def set_parameters(self, a = None, b = None):
        if a is not None:
            self._a = a
            self.calc_area()
        if b is not None:
            self._b = b
            self.calc_area()

if __name__ == "__main__":
    rec = Rectangle(4, 5)
    print(rec.area)
    print(rec.calc_diagonal())


