"""Exercise the real image's configured Python entrypoint without provider credentials."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time


def verify_image(image: str) -> dict:
    inspected = subprocess.run(
        ["docker", "image", "inspect", image],
        capture_output=True, text=True, check=True, timeout=30,
    )
    metadata = json.loads(inspected.stdout)[0]
    command = metadata["Config"]["Cmd"]
    if not isinstance(command, list) or not command or command[-1] != "start":
        raise ValueError("Expected the actual image's start command")
    # Preserve all configured import/path flags; only request CLI help instead of joining Cloud.
    probe = ["docker", "run", "--rm", "--network=none", image, *command[:-1], "--help"]
    started = time.monotonic()
    child = subprocess.Popen(probe, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output, _ = child.communicate(timeout=300)
    print(output.decode(errors="replace"), flush=True)
    result = {
        "command": probe, "executed": True, "pid": child.pid,
        "exit_code": child.returncode, "elapsed_seconds": time.monotonic() - started,
        "image_id": metadata["Id"], "configured_command": command,
        "output_sha256": hashlib.sha256(output).hexdigest(),
        "scope": "Actual isolated image startup imports only; no provider or STT acceptance",
    }
    print(json.dumps(result), flush=True)
    if child.returncode != 0:
        raise subprocess.CalledProcessError(child.returncode, probe)
    if not output.strip():
        raise AssertionError("Worker CLI produced no help output")
    script = next(part for part in command if part.startswith("/app/") and part.endswith(".py"))
    serialization_check = f"""
import importlib.util, json, pickle, sys
spec = importlib.util.spec_from_file_location('worker_process_check', {script!r})
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
handler = module.create_server()._entrypoint_fnc
assert pickle.loads(pickle.dumps(handler)) is handler
print(json.dumps(dict(handler=handler.__qualname__, serialization='PASS')))
"""
    process_probe = ["docker", "run", "--rm", "--network=none", image, command[0], "-P", "-c", serialization_check]
    with subprocess.Popen(process_probe, stdout=subprocess.PIPE, stderr=subprocess.STDOUT) as process:
        process_output, _ = process.communicate(timeout=300)
        print(process_output.decode(errors="replace"), flush=True)
        print(json.dumps({"command": process_probe, "executed": True, "pid": process.pid,
                          "exit_code": process.returncode, "image_id": metadata["Id"],
                          "output_sha256": hashlib.sha256(process_output).hexdigest(),
                          "scope": "Actual isolated SDK registered-handler pickle check; no provider acceptance"}), flush=True)
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, process_probe)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image")
    verify_image(parser.parse_args().image)
