from typing import Optional
import os
import subprocess
import tempfile
import mss
import mss.tools
from core.logger import logger


class GUIHandler:
    _last_error: Optional[str] = None  # Store last error for reporting
    
    @classmethod
    def _get_docker_container(cls) -> Optional[str]:
        """Get Docker container name/ID from environment variable."""
        return os.getenv("GUI_DOCKER_CONTAINER", None)

    @classmethod
    def _get_docker_display(cls) -> str:
        """Get DISPLAY environment variable for Docker container."""
        return os.getenv("GUI_DOCKER_DISPLAY", ":0")
    
    @classmethod
    def get_last_error(cls) -> Optional[str]:
        """Get the last error message from screenshot capture, if any."""
        return cls._last_error

    @classmethod
    def _capture_from_docker(cls, container: str, display: str) -> Optional[bytes]:
        """
        Capture screenshot from Docker container.
        Returns PNG bytes or None on failure.
        Uses docker exec with inline Python to avoid file copy issues.
        """
        try:
            # Use inline Python command to avoid docker cp issues with volume mounts
            # The script is passed directly to python3 -c
            python_cmd = f"""
import sys
import os
import mss
import mss.tools
import base64

# Set DISPLAY
os.environ['DISPLAY'] = '{display}'

try:
    with mss.mss() as sct:
        monitors = sct.monitors
        # Primary monitor is index 1 if available
        monitor = monitors[1] if len(monitors) > 1 else monitors[0]
        shot = sct.grab(monitor)
        png_bytes = mss.tools.to_png(
            shot.rgb,
            shot.size,
            output=None,
        )
        # Write to stdout as base64 to avoid binary issues
        print(base64.b64encode(png_bytes).decode('utf-8'))
        sys.exit(0)
except Exception as e:
    print(f"ERROR: {{str(e)}}", file=sys.stderr)
    sys.exit(1)
"""

            # Execute Python command directly in container (no file copy needed)
            exec_cmd = [
                "docker", "exec",
                "-e", f"DISPLAY={display}",
                container,
                "python3", "-c", python_cmd
            ]

            exec_proc = subprocess.run(
                exec_cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if exec_proc.returncode != 0:
                error_msg = f"Screenshot capture failed in container: {exec_proc.stderr.strip()}"
                logger.warning(f"[ScreenState] {error_msg}")
                cls._last_error = error_msg
                return None

            # Decode base64 output
            import base64
            stdout_content = exec_proc.stdout.strip()
            if not stdout_content:
                error_msg = "Screenshot capture returned empty output"
                logger.warning(f"[ScreenState] {error_msg}")
                cls._last_error = error_msg
                return None
                
            png_bytes = base64.b64decode(stdout_content)
            return png_bytes

        except subprocess.TimeoutExpired:
            error_msg = "Screenshot capture timed out in Docker container"
            logger.warning(f"[ScreenState] {error_msg}")
            cls._last_error = error_msg
            return None
        except Exception as e:
            error_msg = f"Docker screenshot capture failed: {e}"
            logger.warning(f"[ScreenState] {error_msg}")
            cls._last_error = error_msg
            return None

    @classmethod
    def get_screen_state(cls) -> Optional[bytes]:
        """
        Capture the primary monitor and return PNG bytes in memory.
        If GUI_DOCKER_CONTAINER is set, captures from the Docker container.
        Otherwise, captures from the local host.
        Returns None on failure.
        """
        # Check if we should capture from Docker container
        docker_container = cls._get_docker_container()
        if docker_container:
            display = cls._get_docker_display()
            png_bytes = cls._capture_from_docker(docker_container, display)
            if png_bytes is not None:
                return png_bytes
            # Fall through to local capture if Docker fails

        # Local capture (fallback or default)
        try:
            with mss.mss() as sct:
                monitors = sct.monitors

                # Primary monitor is index 1 if available
                monitor = monitors[1] if len(monitors) > 1 else monitors[0]

                shot = sct.grab(monitor)
                png_bytes = mss.tools.to_png(
                    shot.rgb,
                    shot.size,
                    output=None,
                )

                return png_bytes

        except Exception as e:
            error_msg = f"Local screenshot capture failed: {e}"
            logger.warning(f"[ScreenState] {error_msg}")
            cls._last_error = error_msg
            return None
