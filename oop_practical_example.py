"""Practical OOP example in Python.

Problem: A small library management system.

This script demonstrates key Object-Oriented Programming concepts:
- class and object
- attributes and methods
- encapsulation
- inheritance
- polymorphism
- composition
"""


class Book:
    """Represents a book in the library."""

    def __init__(self, title, author, isbn):
        self.title = title
        self.author = author
        self.isbn = isbn
        self.is_available = True

    def __str__(self):
        status = "Available" if self.is_available else "Borrowed"
        return f"{self.title} by {self.author} ({self.isbn}) - {status}"

    def borrow(self):
        if self.is_available:
            self.is_available = False
            return True
        return False

    def return_book(self):
        if not self.is_available:
            self.is_available = True
            return True
        return False


class Member:
    """Represents a library member."""

    def __init__(self, name, member_id):
        self.name = name
        self.member_id = member_id
        self.borrowed_books = []

    def borrow_book(self, book, library):
        if len(self.borrowed_books) >= 3:
            print(f"{self.name} has reached the borrowing limit.")
            return False

        if library.lend_book(book, self):
            self.borrowed_books.append(book)
            return True
        return False

    def return_book(self, book, library):
        if book in self.borrowed_books:
            if library.receive_book(book, self):
                self.borrowed_books.remove(book)
                return True
        return False

    def __str__(self):
        return f"Member: {self.name} (ID: {self.member_id})"


class VIPMember(Member):
    """A special member type with a higher borrowing limit."""

    def __init__(self, name, member_id):
        super().__init__(name, member_id)
        self.max_books = 5

    def borrow_book(self, book, library):
        if len(self.borrowed_books) >= self.max_books:
            print(f"{self.name} has reached the VIP borrowing limit.")
            return False

        if library.lend_book(book, self):
            self.borrowed_books.append(book)
            return True
        return False


class Library:
    """The central system that manages books and members."""

    def __init__(self):
        self.books = []
        self.members = []

    def add_book(self, book):
        self.books.append(book)

    def register_member(self, member):
        self.members.append(member)

    def find_book(self, isbn):
        for book in self.books:
            if book.isbn == isbn:
                return book
        return None

    def lend_book(self, book, member):
        if book in self.books and book.is_available:
            if member in self.members:
                book.borrow()
                return True
        print("Book cannot be lent out.")
        return False

    def receive_book(self, book, member):
        if book in self.books and not book.is_available:
            book.return_book()
            return True
        print("This book cannot be returned.")
        return False

    def show_available_books(self):
        available = [book for book in self.books if book.is_available]
        print("\nAvailable books:")
        for book in available:
            print(f"- {book.title} by {book.author}")


# -----------------------------
# Demo / Example usage
# -----------------------------
if __name__ == "__main__":
    library = Library()

    book1 = Book("Python for Beginners", "Alice Johnson", "978-1-234")
    book2 = Book("Data Structures", "Sam Lee", "978-9-876")
    book3 = Book("OOP in Python", "Mina Patel", "978-5-432")
    book4 = Book("Machine Learning Basics", "Nora Chen", "978-6-789")

    library.add_book(book1)
    library.add_book(book2)
    library.add_book(book3)
    library.add_book(book4)

    member1 = Member("John", "M001")
    member2 = VIPMember("Sarah", "M002")

    library.register_member(member1)
    library.register_member(member2)

    print("Initial state:")
    library.show_available_books()

    print("\nJohn borrows Python for Beginners")
    member1.borrow_book(book1, library)
    print(f"John's books: {[book.title for book in member1.borrowed_books]}")

    print("\nSarah borrows Data Structures")
    member2.borrow_book(book2, library)
    print(f"Sarah's books: {[book.title for book in member2.borrowed_books]}")

    print("\nSarah tries to borrow another book")
    member2.borrow_book(book3, library)
    print(f"Sarah's books: {[book.title for book in member2.borrowed_books]}")

    print("\nReturning Data Structures")
    member2.return_book(book2, library)
    print(f"Sarah's books after return: {[book.title for book in member2.borrowed_books]}")

    print("\nFinal library status:")
    for book in library.books:
        print(book)

    # Explanation of OOP concepts
    print("\nOOP concepts used here:")
    print("- Class: Book, Member, VIPMember, Library")
    print("- Object: each instance like book1, member1, library")
    print("- Attributes: title, author, member_id, borrowed_books")
    print("- Methods: borrow_book(), return_book(), lend_book()")
    print("- Inheritance: VIPMember inherits from Member")
    print("- Encapsulation: data is protected inside each class")
    print("- Polymorphism: different classes can implement borrow_book() in different ways")
