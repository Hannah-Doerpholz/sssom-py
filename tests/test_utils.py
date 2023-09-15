"""Test for merging MappingSetDataFrames."""

import unittest

import yaml
from curies import Converter

from sssom.constants import OBJECT_ID, SUBJECT_ID
from sssom.context import SSSOM_BUILT_IN_PREFIXES
from sssom.io import extract_iri
from sssom.parsers import parse_sssom_table
from sssom.util import (
    MappingSetDataFrame,
    filter_out_prefixes,
    filter_prefixes,
    get_prefixes_used_in_table,
    inject_metadata_into_df,
    invert_mappings,
)
from tests.constants import data_dir


class TestIO(unittest.TestCase):
    """A test case for merging msdfs."""

    def setUp(self) -> None:
        """Set up."""
        self.msdf = parse_sssom_table(f"{data_dir}/basic.tsv")
        self.msdf2 = parse_sssom_table(f"{data_dir}/basic7.tsv")
        self.features = [SUBJECT_ID, OBJECT_ID]

    def test_broken_predicate_list(self):
        """Test merging of multiple msdfs."""
        pred_filter_list = ["skos:relatedMatch", f"{data_dir}/predicate_list3.txt"]
        prefix_map = {"skos": "http://www.w3.org/2004/02/skos/core#"}
        converter = Converter.from_prefix_map(prefix_map)
        iri_list = []
        for p in pred_filter_list:
            p_iri = extract_iri(p, converter)
            if p_iri:
                iri_list.extend(p_iri)
        self.assertEqual(3, len(iri_list))

    def test_filter_prefixes_any(self):
        """Test filtering MSDF.df by prefixes provided."""
        prefix_filter_list = ["x", "y"]
        original_msdf = self.msdf
        filtered_df = filter_prefixes(
            original_msdf.df,
            prefix_filter_list,
            self.features,
            require_all_prefixes=False,
        )
        self.assertEqual(len(filtered_df), 136)

    def test_filter_prefixes_all(self):
        """Test filtering MSDF.df by prefixes provided."""
        prefix_filter_list = ["x", "y"]
        original_msdf = self.msdf
        filtered_df = filter_prefixes(
            original_msdf.df,
            prefix_filter_list,
            self.features,
            require_all_prefixes=True,
        )
        self.assertEqual(len(filtered_df), 40)

    def test_filter_out_prefixes_any(self):
        """Test filtering MSDF.df by prefixes provided."""
        prefix_filter_list = ["x", "y"]
        original_msdf = self.msdf
        filtered_df = filter_out_prefixes(
            original_msdf.df,
            prefix_filter_list,
            self.features,
            require_all_prefixes=False,
        )
        self.assertEqual(len(filtered_df), 5)

    def test_filter_out_prefixes_all(self):
        """Test filtering MSDF.df by prefixes provided."""
        prefix_filter_list = ["x", "y"]
        original_msdf = self.msdf
        filtered_df = filter_out_prefixes(
            original_msdf.df,
            prefix_filter_list,
            self.features,
            require_all_prefixes=True,
        )
        self.assertEqual(len(filtered_df), 101)

    def test_remove_mappings(self):
        """Test remove mappings."""
        prefix_filter_list = ["x", "y"]
        original_msdf = self.msdf
        filtered_df = filter_out_prefixes(original_msdf.df, prefix_filter_list, self.features)
        new_msdf = MappingSetDataFrame.with_converter(
            df=filtered_df,
            converter=original_msdf.converter,
            metadata=original_msdf.metadata,
        )
        original_length = len(original_msdf.df)
        original_msdf.remove_mappings(new_msdf)
        # len(self.msdf.df) = 141 and len(new_msdf.df) = 5
        self.assertEqual(len(original_msdf.df), original_length - len(new_msdf.df))

    def test_clean_prefix_map(self):
        """Test clean prefix map."""
        prefix_filter_list = ["x", "y"]
        original_msdf = self.msdf
        filtered_df = filter_out_prefixes(original_msdf.df, prefix_filter_list, self.features)
        new_msdf = MappingSetDataFrame.with_converter(
            df=filtered_df,
            converter=original_msdf.converter,
            metadata=original_msdf.metadata,
        )
        new_msdf.clean_prefix_map()
        self.assertEqual(
            new_msdf.prefix_map.keys(),
            set(original_msdf.prefix_map.keys()).intersection(set(new_msdf.prefix_map.keys())),
        )

    def test_clean_prefix_map_strict(self):
        """Test clean prefix map with 'strict'=True."""
        msdf = parse_sssom_table(f"{data_dir}/test_clean_prefix.tsv")
        with self.assertRaises(ValueError):
            msdf.clean_prefix_map(strict=True)

    def test_clean_prefix_map_not_strict(self):
        """Test clean prefix map with 'strict'=False."""
        msdf = parse_sssom_table(f"{data_dir}/test_clean_prefix.tsv")
        original_curie_map = msdf.prefix_map
        self.assertEqual(
            {"a", "b", "c", "d", "orcid"}.union(SSSOM_BUILT_IN_PREFIXES),
            set(original_curie_map),
        )
        msdf.clean_prefix_map(strict=False)
        new_curie_map = msdf.prefix_map
        self.assertEqual(
            {"a", "b", "c", "d", "orcid", "x1", "y1", "z1"}.union(SSSOM_BUILT_IN_PREFIXES),
            set(new_curie_map),
        )

    def test_invert_nodes(self):
        """Test invert nodes."""
        subject_prefix = "a"
        inverted_df = invert_mappings(self.msdf2.df, subject_prefix, False)
        self.assertEqual(len(inverted_df), 13)

    def test_invert_nodes_merged(self):
        """Test invert nodes with merge_inverted."""
        subject_prefix = "a"
        inverted_df = invert_mappings(self.msdf2.df, subject_prefix, True)
        self.assertEqual(len(inverted_df), 38)

    def test_invert_nodes_without_prefix(self):
        """Test invert nodes."""
        inverted_df = invert_mappings(df=self.msdf2.df, merge_inverted=False)
        self.assertEqual(len(inverted_df), len(self.msdf2.df.drop_duplicates()))

    def test_inject_metadata_into_df(self):
        """Test injecting metadata into DataFrame is as expected."""
        expected_creators = "orcid:0000-0001-5839-2535|orcid:0000-0001-5839-2532"
        msdf = parse_sssom_table(f"{data_dir}/test_inject_metadata_msdf.tsv")
        msdf_with_meta = inject_metadata_into_df(msdf)
        creator_ids = msdf_with_meta.df["creator_id"].drop_duplicates().values.item()
        self.assertEqual(creator_ids, expected_creators)


class TestUtils(unittest.TestCase):
    """Unit test for utility functions."""

    def test_get_prefixes(self):
        """Test getting prefixes from a MSDF."""
        path = data_dir.joinpath("enm_example.tsv")
        metadata_path = data_dir.joinpath("enm_example.yml")
        metadata = yaml.safe_load(metadata_path.read_text())
        msdf = parse_sssom_table(path, meta=metadata)
        prefixes = get_prefixes_used_in_table(msdf.df, converter=msdf.converter)
        self.assertNotIn("http", prefixes)
        self.assertNotIn("https", prefixes)
        self.assertEqual(
            {
                "ENVO",
                "NPO",
                "ENM",
                "CHEBI",
                "OBI",
                "IAO",
                "BAO",
                "EFO",
                "BTO",
                "orcid",
            }.union(SSSOM_BUILT_IN_PREFIXES),
            prefixes,
        )
