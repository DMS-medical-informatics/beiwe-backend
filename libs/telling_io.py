from _io import BytesIO

# Keep track of our effective "offset" even when we empty the buffer with empty()
# by override BytesIO tell method.
class TellingBytesIO(BytesIO):
    _position = 0

    def __init__(self):
        BytesIO.__init__(self)

    def tell(self):
        return self._position + super(TellingBytesIO, self).tell()

    def empty(self):
        self._position = self.tell()
        self.seek(0)
        self.truncate(0)

