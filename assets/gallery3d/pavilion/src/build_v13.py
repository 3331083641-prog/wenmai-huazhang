import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
if os.path.join(ROOT, "blender") not in sys.path:
    sys.path.insert(0, os.path.join(ROOT, "blender"))

from pavilionlib.assemble13 import main  # noqa: E402

if __name__ == "__main__":
    main()