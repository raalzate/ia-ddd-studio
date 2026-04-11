import io
import sys


class Tee(io.StringIO):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stdout = sys.stdout

    def write(self, s):
        self.stdout.write(s)
        super().write(s)

    def flush(self):
        self.stdout.flush()
        super().flush()
