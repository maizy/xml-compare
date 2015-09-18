#!/usr/bin/env python
# encoding: utf-8

# Copyright: Nikita Kovalev, 2015, HeadHunter
#
# based on code originally writen by me in
# https://github.com/hhru/frontik/blob/01ed1ea15c0b4cdf4c5e4e380c176dd0bb21d2d9/frontik/testing/xml_asserts.py

from __future__ import print_function
import argparse
import itertools

from lxml import etree

__version__ = '0.1'


def _describe_element(elem):
    root = elem.getroottree()
    if not root:
        return '? [tag name: {}]'.format(elem.tag)
    else:
        return root.getpath(elem)


def _xml_text_compare(t1, t2):
    return (t1 or '').strip() == (t2 or '').strip()


def _xml_tags_compare(a, b):
    # (1): compare tag names
    res = cmp(a.tag, b.tag)
    if res != 0:
        return res

    # (2): compare attributes
    res = cmp(dict(a.attrib), dict(b.attrib))
    if res != 0:
        return res

    # (3): compare children
    a_children = a.getchildren()
    b_children = b.getchildren()
    a_children.sort(_xml_tags_compare)
    b_children.sort(_xml_tags_compare)
    for a_child, b_child in itertools.izip_longest(a_children, b_children):
        child_res = cmp(a_child, b_child)
        if child_res != 0:
            res = child_res
            break

    return res


def xml_compare_tag_attribs_text(xml1, xml2, reporter, compare_xml2_attribs=True):
    if xml1.tag != xml2.tag:
        reporter('Tags do not match: {tag1} and {tag2} (path: {path})'
                 .format(tag1=xml1.tag, tag2=xml2.tag, path=_describe_element(xml1)))
        return False

    for attrib, value in xml1.attrib.iteritems():
        if xml2.attrib.get(attrib) != value:
            reporter('Attributes do not match: {attr}={v1!r}, {attr}={v2!r} (path: {path})'
                     .format(attr=attrib, v1=value, v2=xml2.attrib.get(attrib), path=_describe_element(xml1)))
            return False

    if compare_xml2_attribs:
        for attrib in xml2.attrib:
            if attrib not in xml1.attrib:
                reporter('xml2 has an attribute xml1 is missing: {attrib} (path: {path})'
                         .format(attrib=attrib, path=_describe_element(xml2)))
                return False

    if not _xml_text_compare(xml1.text, xml2.text):
        reporter('Text: {t1} != {t2} (path: {path})'
                 .format(t1=xml1.text.encode('utf-8') if xml1.text else '<none>',
                         t2=xml2.text.encode('utf-8') if xml2.text else '<none>',
                         path=_describe_element(xml1)))
        return False

    if not _xml_text_compare(xml1.tail, xml2.tail):
        reporter('Tail: {tail1} != {tail2}'.format(
            tail1=xml1.tail.encode('utf-8'), tail2=xml2.tail.encode('utf-8'), path=_describe_element(xml1)))
        return False

    return True


class _DownstreamReporter(object):

    def __init__(self):
        self.last_error = None

    def __call__(self, *args, **kwargs):
        self.last_error = args[0]


def xml_compare(xml1, xml2, check_tags_order=False, reporter=lambda x: None):
    """Compare two etree.Element objects.
    Based on https://bitbucket.org/ianb/formencode/src/tip/formencode/doctest_xml_compare.py#cl-70
    """
    if not xml_compare_tag_attribs_text(xml1, xml2, reporter=reporter):
        return False

    children1 = xml1.getchildren()
    children2 = xml2.getchildren()
    if len(children1) != len(children2):
        reporter('Children length differs, {len1} != {len2} (path: {path})'
                 .format(len1=len(children1), len2=len(children2), path=_describe_element(xml1)))
        return False

    if not check_tags_order:
        children1.sort(_xml_tags_compare)
        children2.sort(_xml_tags_compare)

    i = 0
    for c1, c2 in zip(children1, children2):
        i += 1
        if not xml_compare(c1, c2, check_tags_order, reporter):
            reporter('Children not matched (path: {path})'
                     .format(n=i, tag1=c1.tag, tag2=c2.tag, path=_describe_element(xml1)))
            return False

    return True


def xml_check_compatibility(old_xml, new_xml, reporter=lambda x: None):
    """Check compatibility of two xml documents (new_xml is an extension of old_xml).
    new_xml >= old_xml:
        * new_xml should contains all attribs and properties from old_xml
        * new_xml may have any extra attribs
        * new_xml may have any extra properties
    """
    pre_cmp = xml_compare_tag_attribs_text(old_xml, new_xml, reporter=reporter, compare_xml2_attribs=False)
    if not pre_cmp:
        return False

    old_children = old_xml.getchildren()
    new_children = new_xml.getchildren()

    if len(old_children) == 0:
        return True

    elif len(new_children) < len(old_children):
        reporter('Children length differs, {len1} < {len2} (path: {path})'
                 .format(len1=len(old_children), len2=len(new_children), path=_describe_element(old_xml)))
        return False

    else:
        new_children_index = {}
        for child in new_children:
            tag = child.tag
            if tag not in new_children_index:
                new_children_index[tag] = []
            new_children_index[tag].append(child)
        for tag in new_children_index.iterkeys():
            new_children_index[tag].sort(_xml_tags_compare)

        old_children.sort(_xml_tags_compare)
        for child in old_children:
            tag = child.tag
            if tag not in new_children_index or len(new_children_index[tag]) == 0:
                reporter('Tag {tag} not exist in new xml (path: {path})'
                         .format(tag=tag, path=_describe_element(old_xml)))
                return False

            any_matched = False
            downstream_reporter = _DownstreamReporter()
            for match_child in new_children_index[tag]:
                is_compatible = xml_check_compatibility(child, match_child, downstream_reporter)
                if is_compatible:
                    any_matched = True
                    new_children_index[tag].remove(match_child)
                    break
            if not any_matched:
                reporter(downstream_reporter.last_error)
                return False
        return True


def _parse_args(args):
    parser = argparse.ArgumentParser(description='Compare two xml docs')
    parser.add_argument('old', metavar='OLD_XML', type=argparse.FileType('rb'))
    parser.add_argument('new', metavar='NEW_XML', type=argparse.FileType('rb'))
    parser.add_argument('-m', '--mode', metavar='equal|compatible', default='equal', help='Compare mode')
    parser.add_argument('-o', '--check-order', action='store_true',
                        help="Check tag order (not use in compatible mode)")
    options = parser.parse_args(args=args)
    return options


def main(args):
    options = _parse_args(args)

    old_xml = etree.parse(options.old).getroot()
    new_xml = etree.parse(options.new).getroot()
    mode = options.mode
    reporter = print
    if mode == 'equal':
        res = xml_compare(old_xml, new_xml, check_tags_order=options.check_order, reporter=reporter)
    elif mode == 'compatible':
        res = xml_check_compatibility(old_xml, new_xml, reporter=reporter)
    else:
        print('Unknown mode {}'.format(mode))
        return 2
    return 0 if res else 1


if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv[1:]))
