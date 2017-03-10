from xml.etree.ElementTree import ElementTree


def read_svg(path):
    tree = ElementTree()
    tree.parse(path)
    return tree


def write_svg(tree, out_path):
    tree.write(out_path, encoding="utf-8", xml_declaration=True)
