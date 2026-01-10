import tornado
import tornado.testing
from tornado.testing import AsyncTestCase


# Simple test to verify Tornado async testing framework works
class MyTestCase2(AsyncTestCase):
    def test_framework(self):
        """Test that the async test framework is properly configured."""
        # Verify we can create an AsyncTestCase
        assert self is not None

        # Verify the io_loop is available
        assert hasattr(self, 'io_loop')
        assert self.io_loop is not None

