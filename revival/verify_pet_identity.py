"""Pet template/key ordering at the original refresh consumer seam."""
import struct
from inventory import pet_record
from native_gameplay_probe import probe


def main():
    payload = pet_record({'id':7,'template_id':500001,'name':'身份校验'})
    _, native = probe(0xf89ba0,0xf5df70,0xf5f1f0,payload=payload)
    # SRefreshPetData stores the Pet bean at +8. Native process 1134ff7
    # loads message+10 (bean+8) and passes it to manager lookup 112ffd0.
    # 1135013 loads message+c (bean+4) into internal template field +4.
    assert struct.unpack_from('<i',native,8)[0] == 7, 'Native pet lookup received template instead of instance key'
    assert struct.unpack_from('<i',native,4)[0] == 500001
    print('PASS native pet consumer receives distinct template and instance key')


if __name__ == '__main__':
    main()
