"""Unit tests for the NLIVerificationService."""

import pytest
from app.services.nli.verifier import NLIVerificationService


def test_nli_entailment_match():
    nli = NLIVerificationService()
    claim = "The Eiffel Tower is located in Paris."
    evidence = "The Eiffel Tower is a famous landmark located in Paris, France."
    res = nli.verify_pair(claim, evidence)

    assert res.entailment > res.contradiction
    assert res.label == "SUPPORTED"


def test_nli_year_contradiction():
    nli = NLIVerificationService()
    claim = "Google was founded in 1999."
    evidence = "Google was founded in 1998 by Larry Page and Sergey Brin."
    res = nli.verify_pair(claim, evidence)

    assert res.contradiction > res.entailment
    assert res.label == "CONTRADICTED"
