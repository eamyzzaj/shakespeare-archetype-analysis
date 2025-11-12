import nltk


def extract_charcs_xml(lit_work: list, print_charcs=False):
    main_charcs = []
    side_charcs = []

    for p in lit_work:
        for l in p.itertext():
            if p.tag == "TITLE":
                title = l.strip()
        if p.tag == "PERSONAE":
            lines = [l.strip() for l in p.itertext() if l.strip()]
            if lines and "Dramatis Personae" in lines[0]:
                lines.pop(0)

            group = []  # stores consecutive uppercase names

            for line in lines:
                # Case 1: fully uppercase line (part of a grouped name block)
                if line.isupper():
                    group.append(line)
                    continue

                # Case 2: description following a group of uppercase names
                if group:
                    desc = line.strip(". ")
                    prefix = "(of the group) " if len(group) > 1 else ""
                    for name in group:
                        main_charcs.append({
                            "name": name,
                            "desc": prefix + desc
                        })
                    group = []
                    continue

                # Case 3: single-line entry (name + comma + desc)
                if "," in line:
                    name_part, desc_part = line.split(",", 1)
                    name_part, desc_part = name_part.strip(), desc_part.strip(". ")

                    # If the first "word" is ALL CAPS, treat as main character.
                    first_word = name_part.split()[0]
                    if first_word.isupper():
                        main_charcs.append({
                            "name": name_part,
                            "desc": desc_part
                        })
                    else:
                        side_charcs.append({"desc": line.strip(". ")})
                    continue

                # Case 4: other lines (no comma)
                first_word = line.split()[0]
                if first_word.isupper():
                    main_charcs.append({"name": line, "desc": ""})
                else:
                    side_charcs.append({"desc": line.strip(". ")})

            # Handle any leftover uppercase names
            for name in group:
                main_charcs.append({"name": name, "desc": ""})

    if print_charcs:
        # -------- Output --------
        print("="*50)
        print(f"{title}")
        print("="*50)
        print("Main Characters:")
        for c in main_charcs:
            print(f" - {c['name']}: {c['desc']}")

        print("\nSide Characters:")
        for c in side_charcs:
            print(f" - {c['desc']}")

        print("\n\n")
    
    return main_charcs, side_charcs


def parse_play_xml(xml_tree):
    """
    Parses a Shakespeare XML play into a structured dictionary.
    Includes characters, acts, scenes, and per-scene speech + line counts.
    """
    root = xml_tree
    title = root.find('.//TITLE').text if root.find('.//TITLE') is not None else "Unknown Title"

    # --- Extract characters ---
    chars = root.findall('.//PERSONA')
    group_chars = root.findall('.//PGROUP')
    acts = root.findall('.//ACT')

    main_characters = []
    for char in chars:
        for l in char.itertext():
            l = l.strip()
            if not l:
                continue
            if ',' in l:
                main, desc = l.split(',', 1)
                if main.split()[0].isupper():
                    main_characters.append({
                        "name": main.strip(),
                        "desc": desc.strip()
                    })
            else:
                main_characters.append({
                    "name": l,
                    "desc": ""
                })

    group_characters = []
    for gchar in group_chars:
        desc_elem = gchar.find('.//GRPDESCR')
        desc = desc_elem.text.strip() if desc_elem is not None else "(in group)"
        for char in gchar.findall('.//PERSONA'):
            for l in char.itertext():
                l = l.strip()
                if not l:
                    continue
                group_characters.append({
                    "name": l,
                    "group_desc": f"(in group) {desc}"
                })

    # --- Extract acts, scenes, and speech/line counts ---
    act_data = []
    for act_i, act in enumerate(acts, start=1):
        scenes = act.findall('.//SCENE')
        scene_data = []

        for scene_i, scene in enumerate(scenes, start=1):
            speech_stats = {}  # {speaker_name: {"speeches": n, "lines": n}}
            speakers = []

            for speech in scene.findall('.//SPEECH'):
                # Count lines in this speech
                line_count = len(speech.findall('.//LINE'))
                # There may be multiple speakers (shared speeches)
                for s in speech.findall('.//SPEAKER'):
                    if not s.text:
                        continue
                    name = s.text.strip()
                    speakers.append(name)

                    # initialize if not present
                    if name not in speech_stats:
                        speech_stats[name] = {"speeches": 0, "lines": 0}

                    speech_stats[name]["speeches"] += 1
                    speech_stats[name]["lines"] += line_count

            # Build scene data
            unique_speakers = sorted(set(speakers))
            scene_data.append({
                "scene": scene_i,
                "speakers": [
                    {
                        "name": spkr,
                        "speech_count": speech_stats.get(spkr, {}).get("speeches", 0),
                        "line_count": speech_stats.get(spkr, {}).get("lines", 0)
                    }
                    for spkr in unique_speakers
                ]
            })

        act_data.append({
            "act": act_i,
            "scenes": scene_data
        })

    return {
        "title": title,
        "acts": act_data,
        "main_characters": main_characters,
        "group_characters": group_characters
    }



def merge_play_data(parsed_play, main_charcs, side_charcs):
    """
    Merges the outputs of extract_charcs_xml() and parse_play()
    into a single structure with character descriptions attached
    to each scene's speakers.
    """
    # --- Build a lookup dictionary for quick name → description ---
    char_map = {}

    for c in main_charcs:
        name = (c.get("name") or "").strip().upper()
        if name:
            char_map[name] = c.get("desc", "")
    for c in side_charcs:
        name = (c.get("name") or "").strip().upper()
        if name:
            char_map[name] = c.get("desc", "")
        else:
            # side characters without explicit names
            desc = c.get("desc", "")
            if desc:
                char_map[desc.upper()] = desc

    # --- Merge character descriptions into parsed play data ---
    merged_acts = []
    for act in parsed_play["acts"]:
        act_entry = {"act": act["act"], "scenes": []}
        for scene in act["scenes"]:
            speakers = []
            for s in scene["speakers"]:
                name = s["name"].strip().upper()
                speakers.append({
                    "name": s["name"],
                    "speech_count": s.get("speech_count", 0),
                    "desc": char_map.get(name, "(no description found)")
                })
            act_entry["scenes"].append({
                "scene": scene["scene"],
                "speakers": speakers
            })
        merged_acts.append(act_entry)

    # --- Return unified structure ---
    return {
        "title": parsed_play.get("title", "Unknown Play"),
        "acts": merged_acts,
        "characters": main_charcs + side_charcs
    }


from collections import defaultdict
import pandas as pd

def summarize_play_stats(merged_play, main_charcs=None, side_charcs=None, print_summary=True):
    """
    Summarizes quantitative statistics from a merged Shakespeare play.
    Designed for Tableau export (no visualization here).

    Args:
        merged_play : dict from merge_play_data()
        main_charcs : list of main characters (from extract_charcs_xml)
        side_charcs : list of side characters (from extract_charcs_xml)
        print_summary : whether to print summary stats

    Returns:
        dict containing:
            - play_title
            - total_acts
            - total_scenes
            - total_speeches
            - act_speech_totals
            - main_side_ratio
            - character_df (DataFrame)
    """

    totals = defaultdict(lambda: {"speeches": 0, "scenes": 0})
    total_speeches = 0
    total_scenes = 0
    act_speech_totals = {}

    # --- Tally speeches and scenes ---
    for act in merged_play["acts"]:
        act_total = 0
        for scene in act["scenes"]:
            total_scenes += 1
            for s in scene["speakers"]:
                name = s["name"]
                count = s.get("speech_count", 0)
                totals[name]["speeches"] += count
                if count > 0:
                    totals[name]["scenes"] += 1
                total_speeches += count
                act_total += count
        act_speech_totals[act["act"]] = act_total

    total_acts = len(merged_play["acts"])
    main_count = len(main_charcs) if main_charcs else 0
    side_count = len(side_charcs) if side_charcs else 0
    main_side_ratio = f"{main_count}:{side_count}" if side_count else "N/A"

    # --- Compute derived metrics ---
    data = []
    for name, stats in totals.items():
        speeches = stats["speeches"]
        scenes = stats["scenes"]
        share = (speeches / total_speeches * 100) if total_speeches > 0 else 0
        avg_speeches_per_scene = speeches / scenes if scenes > 0 else 0
        role_type = "main" if main_charcs and any(name.upper() == c["name"].upper() for c in main_charcs) else "side"
        data.append({
            "Play": merged_play["title"],
            "Character": name,
            "Total Speeches": speeches,
            "Scenes Appeared": scenes,
            "Speech Share (%)": round(share, 2),
            "Avg Speeches/Scene": round(avg_speeches_per_scene, 2),
            "Role Type": role_type
        })

    df = pd.DataFrame(data).sort_values("Total Speeches", ascending=False)

    summary = {
        "play_title": merged_play["title"],
        "total_acts": total_acts,
        "total_scenes": total_scenes,
        "total_speeches": total_speeches,
        "act_speech_totals": act_speech_totals,
        "main_side_ratio": main_side_ratio,
        "character_df": df
    }

    # --- Optional text summary ---
    if print_summary:
        print(f"\n{summary['play_title']}")
        print("=" * (len(summary['play_title']) + 3))
        print(f"Acts: {total_acts} | Scenes: {total_scenes} | Total Speeches: {total_speeches}")
        print(f"Main: {main_count} | Side: {side_count} | Ratio: {main_side_ratio}\n")

        print("Act-level speech totals:")
        for act, total in act_speech_totals.items():
            print(f"  Act {act}: {total} speeches")

        print("\nTop 10 characters by speeches:")
        print(df.head(10).to_string(index=False))

    return summary
