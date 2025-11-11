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
                    prefix = "(of the) " if len(group) > 1 else ""
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
