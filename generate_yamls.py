#!/usr/bin/env python3
"""
Generate photor.session.yaml files for session directories.
SAFE MODE: never overwrites existing files, only creates missing ones.
"""

import yaml
from pathlib import Path

BASE = Path("/media/dargonar/bkp_1t_new/portfolio/photos")
FNAME = "photor.session.yaml"

SESSIONS = {
    # ── ADHD project ──
    "adhd": {"session": "adhd", "set": "portfolio", "tags": "tdah,retrato,identidad", "description": "Proyecto ADHD — retratos neurodivergentes"},
    "adhd/angi_adhd": {"session": "angi-adhd", "project": "adhd", "personajes": "angi", "tags": "tdah,retrato,identidad"},
    "adhd/facu_adhd": {"session": "facu-adhd", "project": "adhd", "personajes": "facu", "tags": "tdah,retrato,identidad"},
    "adhd/gero_adhd": {"session": "gero-adhd", "project": "adhd", "personajes": "gero", "tags": "tdah,retrato,identidad"},
    "adhd/michelle_adhd": {"session": "michelle-adhd", "project": "adhd", "personajes": "michelle", "tags": "tdah,retrato,identidad"},
    "adhd/monse_adhd": {"session": "monse-adhd", "project": "adhd", "personajes": "monse", "tags": "tdah,retrato,identidad"},
    "adhd/valentin_adhd": {"session": "valentin-adhd", "project": "adhd", "personajes": "valentin", "tags": "tdah,retrato,identidad"},

    # ── Andi ──
    "andi_fast": {"session": "at-home", "project": "andy", "personajes": "andy", "location": "La Plata", "tags": "desnudo,flash"},
    "andi_fast/raw": {"session": "at-home", "project": "andy", "personajes": "andy", "set": "raw"},

    # ── Agustín Araño ──
    "agustin-arano_rock": {"session": "agustin-arano-rock", "project": "agustin-arano", "personajes": "agustin", "tags": "rock,musica,show", "location": "La Plata"},

    # ── Barrio Hipódromo ──
    "barrio_hipodromo": {"session": "barrio-hipodromo", "location": "La Plata", "tags": "street,urbano,arquitectura"},

    # ── Box Cami Nieva ──
    "box_cami_nieva": {"session": "box-cami-nieva", "project": "box", "personajes": "cami", "tags": "boxeo,deporte,retrato", "location": "La Plata"},

    # ── Brenda ──
    "brenda_oleo-al-agua": {"session": "brenda-pileta-kinky", "project": "brenda", "personajes": "brenda,maya", "location": "La Plata", "tags": "pileta,agua,reflejos,kinky", "description": "Brenda — Oleo al agua, experimentación con texturas y reflejos"},

    # ── BW ──
    "bw": {"session": "bw", "set": "selected", "tags": "bw,blanco-y-negro,monocromo,rejunte", "description": "Rejunte de fotos blanco y negro"},

    # ── Circus ──
    "circus": {"session": "circus", "set": "portfolio", "tags": "circo,performance,arte"},
    "circus/backstage": {"session": "backstage", "project": "circus", "tags": "circo,detras-de-escena"},
    "circus/fici": {"session": "fici", "project": "circus", "tags": "circo,festival,internacional"},
    "circus/lu_cianciosi": {"session": "lu-cianciosi", "project": "circus", "personajes": "lu", "tags": "circo,retrato"},
    "circus/payaso_ancla": {"session": "payaso-ancla", "project": "circus", "tags": "circo,payaso,arte"},
    "circus/trape": {"session": "trape", "project": "circus", "tags": "circo,trapecio,arte"},

    # ── Colombia ──
    "colombia": {"session": "colombia", "project": "colombia", "location": "Colombia", "tags": "viaje,paisaje,urbano,selva,naturaleza,playa"},

    # ── Costa Rica ──
    "costa-rica": {"session": "costa-rica", "project": "costa-rica", "set": "portfolio", "location": "Costa Rica", "tags": "viaje,paisaje,selva,naturaleza,playa"},

    # ── Cultural ──
    "cultural/murga": {"session": "murga", "project": "cultural", "tags": "murga,cultura-popular,performance"},
    "cultural/teatro_argentino": {"session": "teatro-argentino", "project": "cultural", "location": "La Plata", "tags": "teatro,arquitectura"},
    "cultural/temazcal": {"session": "temazcal", "project": "cultural", "tags": "ceremonia,ritual,temazcal"},

    # ── Érica ──
    "erica-cita_habitar": {"session": "cita-habitar", "project": "erica", "personajes": "erica", "tags": "intimo,habitar,espacio", "location": "La Plata"},

    # ── Europa ──
    "europa/2023": {"session": "europa-2023", "project": "europa", "tags": "viaje,europa"},
    "europa/2023/amsterdam": {"session": "amsterdam", "project": "europa-2023", "location": "Amsterdam", "tags": "viaje,europa,ciudad"},
    "europa/2023/berlin": {"session": "berlin-2023", "project": "europa-2023", "location": "Berlín", "tags": "viaje,europa,ciudad"},
    "europa/2023/granada": {"session": "granada-2023", "project": "europa-2023", "location": "Granada", "tags": "viaje,europa,ciudad"},
    "europa/2023/malaga": {"session": "malaga", "project": "europa-2023", "location": "Málaga", "tags": "viaje,europa,ciudad"},
    "europa/2023/prague": {"session": "prague", "project": "europa-2023", "location": "Praga", "tags": "viaje,europa,ciudad"},
    "europa/2023/sevilla": {"session": "sevilla-2023", "project": "europa-2023", "location": "Sevilla", "tags": "viaje,europa,ciudad"},
    "europa/2023/sevilla/celeste_and_tatoos": {"session": "sevilla-celeste-tatoos", "project": "europa-2023", "location": "Sevilla", "tags": "viaje,retrato,tatoos"},
    "europa/2023/toulouse": {"session": "toulouse", "project": "europa-2023", "location": "Toulouse", "tags": "viaje,europa,ciudad"},
    "europa/2023/rotterdam": {"session": "rotterdam", "project": "europa-2023", "location": "Rotterdam", "tags": "viaje,europa,ciudad"},
    "europa/2023/marseille": {"session": "marseille", "project": "europa-2023", "location": "Marseille", "tags": "viaje,europa,ciudad"},
    "europa/2023/clermont": {"session": "clermont", "project": "europa-2023", "location": "Clermont-Ferrand", "tags": "viaje,europa,ciudad"},
    # Aurillac
    "europa/2023/aurillac/1_clown": {"session": "aurillac-clown", "project": "aurillac-2023", "location": "Aurillac", "tags": "circo,aurillac,festival,clown"},
    "europa/2023/aurillac/2_trape": {"session": "aurillac-trape", "project": "aurillac-2023", "location": "Aurillac", "tags": "circo,aurillac,festival,trapecio"},
    "europa/2023/aurillac/apples": {"session": "aurillac-apples", "project": "aurillac-2023", "location": "Aurillac", "tags": "circo,aurillac,festival"},
    "europa/2023/aurillac/cable": {"session": "aurillac-cable", "project": "aurillac-2023", "location": "Aurillac", "tags": "circo,aurillac,cable"},
    "europa/2023/aurillac/ciudad": {"session": "aurillac-ciudad", "project": "aurillac-2023", "location": "Aurillac", "tags": "aurillac,ciudad"},
    "europa/2023/aurillac/elephants": {"session": "aurillac-elephants", "project": "aurillac-2023", "location": "Aurillac", "tags": "circo,aurillac,festival,elefantes"},
    "europa/2023/aurillac/jeanne": {"session": "aurillac-jeanne", "project": "aurillac-2023", "location": "Aurillac", "tags": "circo,aurillac,retrato"},
    "europa/2023/aurillac/la_collective": {"session": "aurillac-la-collective", "project": "aurillac-2023", "location": "Aurillac", "tags": "circo,aurillac,colectivo"},
    "europa/2023/aurillac/theatre_feminist": {"session": "aurillac-theatre-feminist", "project": "aurillac-2023", "location": "Aurillac", "tags": "circo,aurillac,teatro,feminista"},
    # Europa 2025
    "europa/2025": {"session": "europa-2025", "project": "europa", "tags": "viaje,europa"},
    "europa/2025/belgrade": {"session": "belgrade", "project": "europa-2025", "location": "Belgrado", "tags": "viaje,europa,ciudad"},
    "europa/2025/berlin": {"session": "berlin-2025", "project": "europa-2025", "location": "Berlín", "tags": "viaje,europa,ciudad"},
    "europa/2025/budapest": {"session": "budapest", "project": "europa-2025", "location": "Budapest", "tags": "viaje,europa,ciudad"},
    "europa/2025/granada": {"session": "granada-2025", "project": "europa-2025", "location": "Granada", "tags": "viaje,europa,ciudad"},
    "europa/2025/montenegro": {"session": "montenegro", "project": "europa-2025", "location": "Montenegro", "tags": "viaje,europa,paisaje"},

    # ── Juli Fontán ──
    "juli-fontan/berlin": {"session": "berlin", "project": "juli-fontan", "personajes": "juli", "location": "Berlín", "tags": "viaje,retrato,urbano"},
    "juli-fontan/bs-as_sesion": {"session": "bs-as-sesion", "project": "juli-fontan", "personajes": "juli", "location": "Buenos Aires", "tags": "retrato,intimo"},

    # ── Knots ──
    "knots": {"session": "knots", "tags": "shibari,knots,nudos,cuerdas,bondage"},

    # ── La Plata Techno ──
    "laplata_techno_doxa-aeterna/aeterna": {"session": "aeterna", "project": "laplata-techno", "location": "La Plata", "tags": "techno,fiesta,nocturno"},
    "laplata_techno_doxa-aeterna/club_indie": {"session": "club-indie", "project": "laplata-techno", "location": "La Plata", "tags": "club,indie,nocturno,musica"},

    # ── Malena BW ──
    "malena_bw": {"session": "malena-bw", "personajes": "malena", "tags": "bw,blanco-y-negro,retrato"},

    # ── Marchas ──
    "marchas/antorchas": {"session": "antorchas", "project": "marchas", "location": "La Plata", "tags": "marcha,protesta,antorchas,nocturno"},
    "marchas/congreso": {"session": "congreso", "project": "marchas", "location": "Buenos Aires", "tags": "marcha,protesta,congreso"},
    "marchas/marcha_educacion": {"session": "marcha-educacion", "project": "marchas", "tags": "marcha,protesta,educacion"},
    "marchas/marcha_memoria": {"session": "marcha-memoria", "project": "marchas", "tags": "marcha,protesta,memoria,24m"},
    "marchas/pride_quiero-ser-quien-soy": {"session": "pride", "project": "marchas", "tags": "marcha,pride,diversidad,lgtb"},

    # ── Meme ──
    "meme/lightning": {"session": "lightning", "project": "meme", "personajes": "meme", "tags": "performance,arte,luz"},
    "meme/model": {"session": "model", "project": "meme", "personajes": "meme", "tags": "modelo,retrato,arte"},

    # ── Memo ──
    "memo/session": {"session": "memo-session", "project": "memo", "tags": "intimo,archivo-familiar"},
    "memo/2017-12-12_marina_naked": {"session": "marina-naked-2017", "project": "memo", "personajes": "marina", "tags": "desnudo,intimo"},
    "memo/2017_nov-dic_marina_naked": {"session": "marina-naked-2017-nov", "project": "memo", "personajes": "marina", "tags": "desnudo,intimo"},
    "memo/2017-dic_garchando": {"session": "2017-dic-garchando", "project": "memo", "tags": "archivo,intimo,erotico"},
    "memo/2018-ene-feb-bariloche-desnudo": {"session": "bariloche-desnudo-2018", "project": "memo", "location": "Bariloche", "tags": "desnudo,naturaleza"},

    # ── Michelle ──
    "michelle/geografia_intima": {"session": "geografia-intima", "project": "michelle", "personajes": "michelle", "tags": "intimo,geografia,cuerpo", "description": "Michelle — Geografía Íntima"},
    "michelle/michele_and_flor": {"session": "michele-and-flor", "project": "michelle", "personajes": "michelle,flor", "tags": "duo,intimo,amistad"},

    # ── Mila ──
    "mila/beach": {"session": "beach", "project": "mila", "personajes": "mila", "tags": "playa,verano,body-dialogues"},
    "mila/only-fans": {"session": "only-fans", "project": "mila", "personajes": "mila", "tags": "onlyfans,intimo,erotico"},
    "mila/villa-elisa": {"session": "villa-elisa", "project": "mila", "personajes": "mila", "location": "Villa Elisa", "tags": "interior,intimo,retrato"},

    # ── Misscomplejo ──
    "misscomplejo/flor": {"session": "flor", "project": "misscomplejo", "personajes": "flor", "tags": "body-dialogues,desnudo,intimo"},
    "misscomplejo/gero": {"session": "gero", "project": "misscomplejo", "personajes": "gero", "tags": "body-dialogues,desnudo,intimo"},
    "misscomplejo/grupal": {"session": "grupal", "project": "misscomplejo", "tags": "body-dialogues,grupal,performance"},
    "misscomplejo/lucy": {"session": "lucy", "project": "misscomplejo", "personajes": "lucy", "tags": "body-dialogues,desnudo,intimo"},
    "misscomplejo/nena": {"session": "nena", "project": "misscomplejo", "personajes": "nena", "tags": "body-dialogues,desnudo,intimo"},
    "misscomplejo/orquidea": {"session": "orquidea", "project": "misscomplejo", "personajes": "orquidea", "tags": "body-dialogues,desnudo,intimo"},

    # ── MMA ──
    "mma": {"session": "mma", "tags": "deporte,mma,artes-marciales"},

    # ── Mountain ──
    "mountain/bariloche-memo": {"session": "bariloche-memo", "project": "mountain", "personajes": "memo", "location": "Bariloche", "tags": "montaña,naturaleza"},
    "mountain/san_martin": {"session": "san-martin", "project": "mountain", "location": "San Martín de los Andes", "tags": "montaña,naturaleza"},
    "mountain/tdf": {"session": "tdf", "project": "mountain", "location": "Tierra del Fuego", "tags": "montaña,naturaleza"},

    # ── NOA ──
    "noa/salta": {"session": "salta", "project": "noa", "location": "Salta", "tags": "viaje,norte,argentina"},

    # ── Nono ──
    "nono": {"session": "el-nono", "project": "archivo-familiar", "tags": "archivo-familiar,retrato,familia,facultad,abuelo,nono", "description": "El Nono — archivo familiar"},

    # ── Old CV ──
    "old_cv": {"session": "old-cv", "tags": "archivo,retrato,cv"},

    # ── Puka ──
    "puka/dark_sesion": {"session": "dark-sesion", "project": "puka", "personajes": "puka", "tags": "oscuro,contraste,nocturno"},
    "puka/extreme": {"session": "extreme", "project": "puka", "personajes": "puka", "tags": "extremo,deporte,accion"},
    "puka/villa-elisa": {"session": "villa-elisa", "project": "puka", "personajes": "puka", "location": "Villa Elisa", "tags": "interior,intimo,retrato"},

    # ── Sofí ──
    "sofi_el-paisaje-de-la-piel": {"session": "el-paisaje-de-la-piel", "project": "sofi", "personajes": "sofi", "tags": "piel,paisaje,intimo,cuerpo", "description": "Sofí — El paisaje de la piel"},

    # ── Valentín ──
    "valentin/2014_jardin": {"session": "2014-jardin", "project": "valentin", "personajes": "valentin", "tags": "infancia,archivo-familiar,jardin"},
    "valentin/2015_cena_flia": {"session": "2015-cena-familiar", "project": "valentin", "personajes": "valentin", "tags": "familia,archivo-familiar,cena"},
    "valentin/2015_cumple": {"session": "2015-cumple", "project": "valentin", "personajes": "valentin", "tags": "infancia,archivo-familiar,cumpleanos"},
    "valentin/2025_at_home": {"session": "2025-at-home", "project": "valentin", "personajes": "valentin", "tags": "retrato,casa,adolescencia"},
    "valentin/adhd": {"session": "valentin-adhd", "project": "valentin", "personajes": "valentin", "tags": "tdah,retrato,identidad"},
    "valentin/pesca": {"session": "pesca", "project": "valentin", "personajes": "valentin", "tags": "pesca,naturaleza,actividad"},
    "valentin/risas": {"session": "risas", "project": "valentin", "personajes": "valentin", "tags": "infancia,archivo-familiar,risas"},
    "valentin/popurri": {"session": "popurri", "project": "valentin", "personajes": "valentin", "tags": "archivo-familiar,infancia,miscelanea"},
    "valentin/popurri/2012_vacas": {"session": "2012-vacas", "project": "valentin", "personajes": "valentin", "tags": "infancia,vacas"},
    "valentin/popurri/2020_gonnet": {"session": "2020-gonnet", "project": "valentin", "location": "Gonnet", "tags": "infancia,casa"},
    "valentin/popurri/2022_05_museo": {"session": "2022-museo", "project": "valentin", "tags": "infancia,museo"},

    # ── Valparaíso ──
    "valparaiso/doors": {"session": "doors", "project": "valparaiso", "location": "Valparaíso", "tags": "puertas,arquitectura,color,chile"},
    "valparaiso/lecheros": {"session": "lecheros", "project": "valparaiso", "location": "Valparaíso", "tags": "escaleras,cerro,urbano,chile"},
    "valparaiso/mobile": {"session": "mobile", "project": "valparaiso", "location": "Valparaíso", "tags": "mobile,celular,chile"},

    # ── Wildlife ──
    "orcas": {"session": "orcas", "project": "wildlife", "location": "Península Valdés", "tags": "orcas,naturaleza,fauna"},
    "orcas/puerto-piramides": {"session": "puerto-piramides", "project": "wildlife", "location": "Puerto Pirámides", "tags": "ballenas,naturaleza,fauna"},

    # ── Yo Íntimo ──
    "yo_intimo/angi_xxx": {"session": "angi-xxx", "project": "yo-intimo", "personajes": "angi", "tags": "intimo,desnudo,erotico"},
    "yo_intimo/cata": {"session": "cata", "project": "yo-intimo", "personajes": "cata", "tags": "intimo,desnudo,erotico"},
    "yo_intimo/gri": {"session": "gri", "project": "yo-intimo", "personajes": "gri", "tags": "intimo,desnudo,erotico"},
    "yo_intimo/lu": {"session": "lu", "project": "yo-intimo", "personajes": "lu", "tags": "intimo,desnudo,erotico"},
    "yo_intimo/malena": {"session": "malena", "project": "yo-intimo", "personajes": "malena", "tags": "intimo,desnudo,erotico"},
    "yo_intimo/memo": {"session": "memo", "project": "yo-intimo", "personajes": "memo", "tags": "intimo,desnudo,erotico"},
}


def generate():
    created = 0
    skipped = 0
    errors = 0

    for rel_path, metadata in sorted(SESSIONS.items()):
        dir_path = BASE / rel_path
        if not dir_path.exists():
            print(f"⚠️  No existe: {dir_path}")
            errors += 1
            continue

        yaml_path = dir_path / FNAME
        if yaml_path.exists():
            print(f"⏭️  Ya existe: {rel_path}/{FNAME} — no se toca")
            skipped += 1
            continue

        clean = {k: v for k, v in metadata.items() if v and v not in (None, "")}
        with open(yaml_path, "w") as f:
            yaml.dump(clean, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        print(f"✅ CREADO: {rel_path}/{FNAME}")
        created += 1

    print(f"\n📝 {created} creados, {skipped} saltados (ya existían), {errors} errores")


if __name__ == "__main__":
    generate()