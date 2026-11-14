"""Test-only fixed ZIP envelope so semantic mutations reach payload validators."""
import io
import zipfile


def pack(entries):
    output=io.BytesIO()
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_STORED) as archive:
        for name,data in sorted(entries.items()):
            info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0))
            info.create_system=3
            info.external_attr=0o100600 << 16
            archive.writestr(info,data)
    return output.getvalue()
