"""Actual SEnterWorld decoder must keep experience apart from the intro field."""
import struct
from native_gameplay_probe import probe
from world_protocol import world_snapshot
from inspect_client import OUT, write_json


def main():
    results = []
    for experience in (0, 150, 0x123456789):
        role = dict(id=1, name='入服核对', level=1, school=11, shape=1010109,
                    experience=experience)
        body = world_snapshot(role)
        _, decoded = probe(0xfe4160, 0xfe45f0, 0xfe4630, payload=body)
        intro = struct.unpack_from('<Q', decoded, 0x48)[0]
        actual = struct.unpack_from('<Q', decoded, 0xf8)[0]
        assert intro == 0, 'Experience incorrectly changed the independent intro discriminator'
        assert actual == experience, 'Committed experience was not decoded in the real experience slot'
        results.append(dict(experience=experience, native_intro_q64=intro,
                            native_experience_q64=actual))
        # Completed-chapter projection must stay independent even at zero EXP.
        completed = world_snapshot(role, intro_discriminator=1)
        _, decoded_completed = probe(0xfe4160, 0xfe45f0, 0xfe4630, payload=completed)
        assert struct.unpack_from('<Q', decoded_completed, 0x48)[0] == 1
        assert struct.unpack_from('<Q', decoded_completed, 0xf8)[0] == experience
        results.append(dict(experience=experience, native_intro_q64=1,
                            native_experience_q64=experience,
                            intro_mapping_provenance='designed_completed_chapter_projection'))
    write_json(OUT/'evidence/world-snapshot-experience-native.json', dict(cases=results,
        original_decoder='0xfe4630', gui_verified=False, live_role_modified=False))
    print(results)


if __name__ == '__main__':
    main()
