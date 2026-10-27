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
import asyncio, importlib.util, json, os, pickle, sys
spec = importlib.util.spec_from_file_location('worker_process_check', {script!r})
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
from backend.digital_human import agent_worker as packaged_worker
assert 'backend.digital_human.service' not in sys.modules
assert pickle.loads(pickle.dumps(packaged_worker.digital_human_session)) is packaged_worker.digital_human_session
handler = module.create_server()._entrypoint_fnc
assert pickle.loads(pickle.dumps(handler)) is handler
async def verify_configuration():
    # Real SDK construction only: this container has no network or credentials.
    for prefix in ['LIVEKIT', 'LIVEKIT_INFERENCE']:
        os.environ[prefix + '_API_KEY'] = 'isolated-constructor-check'
        os.environ[prefix + '_API_SECRET'] = 'isolated-constructor-check-32-bytes'
    session = module.create_transcription_session()
    assert session.stt._opts.extra_kwargs.get('endpointing') == 300
    assert session.stt._opts.extra_kwargs['endpointing'] <= session.options.endpointing['min_delay'] * 1000
    assert session.options.transcription_timeout == 8.0
    print(json.dumps(dict(handler=handler.__qualname__, serialization='PASS',
                         actualModel=session.stt.model, actualLanguage=session.stt._opts.language,
                         providerEndpointMilliseconds=session.stt._opts.extra_kwargs['endpointing'],
                         originalTranscriptionDeadlineSeconds=session.options.transcription_timeout)))
    await session.stt.aclose()
    for descriptor in ['google/gemini-3.5-transcribe-live', 'cartesia/ink-whisper', 'deepgram/nova-3']:
        os.environ['DIGITAL_HUMAN_STT_MODEL'] = descriptor
        automatic_session = module.create_transcription_session()
        snapshot = module.transcription_config_snapshot(automatic_session)
        encoded = json.dumps(snapshot)
        assert json.loads(encoded)['language'] is None
        assert snapshot['model'] == descriptor
        assert snapshot['transcription_deadline_seconds'] == 8.0
        assert 'isolated-constructor-check' not in encoded
        assert automatic_session.llm is None and automatic_session.tts is None
        print(json.dumps(dict(automaticLanguageSnapshot='PASS', model=descriptor, snapshot=snapshot)))
        await automatic_session.stt.aclose()
asyncio.run(verify_configuration())
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
