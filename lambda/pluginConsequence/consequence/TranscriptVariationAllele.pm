=head1 LICENSE

Copyright [1999-2015] Wellcome Trust Sanger Institute and the EMBL-European Bioinformatics Institute
Copyright [2016-2019] EMBL-European Bioinformatics Institute

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

     http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY kind, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

=cut


=head1 CONTACT

 Please email comments or questions to the public Ensembl
 developers list at <http://lists.ensembl.org/mailman/listinfo/dev>.

 Questions may also be sent to the Ensembl help desk at
 <http://www.ensembl.org/Help/Contact>.

=cut

=head1 NAME

Bio::EnsEMBL::Variation::TranscriptVariationAllele

=head1 SYNOPSIS

    use Bio::EnsEMBL::Variation::TranscriptVariationAllele;

    my $tva = Bio::EnsEMBL::Variation::TranscriptVariationAllele->new(
        -transcript_variation   => $tv,
        -variation_feature_seq  => 'A',
        -is_reference           => 0,
    );

    print "sequence with respect to the transcript: ", $tva->feature_seq, "\n";
    print "sequence with respect to the variation feature: ", $tva->variation_feature_seq, "\n";
    print "consequence SO terms: ", (join ",", map { $_->SO_term } @{ $tva->get_all_OverlapConsequences }), "\n";
    print "amino acid change: ", $tva->pep_allele_string, "\n";
    print "resulting codon: ", $tva->codon, "\n";
    print "reference codon: ", $tva->transcript_variation->get_reference_TranscriptVariationAllele->codon, "\n";
    print "PolyPhen prediction: ", $tva->polyphen_prediction, "\n";
    print "SIFT prediction: ", $tva->sift_prediction, "\n";

=head1 DESCRIPTION

A TranscriptVariationAllele object represents a single allele of a TranscriptVariation.
It provides methods that are specific to the sequence of the allele, such as codon,
peptide etc. Methods that depend only on position (e.g. CDS start) will be found in
the associated TranscriptVariation. Ordinarily you will not create these objects
yourself, but instead you would create a TranscriptVariation object which will then
construct TranscriptVariationAlleles based on the allele string of the associated
VariationFeature.

Note that any methods that are not specific to Transcripts will be found in the
VariationFeatureOverlapAllele superclass.

=cut

package consequence::TranscriptVariationAllele;

use strict;
use warnings;

use consequence::ProteinFunctionPredictionMatrix qw($AA_LOOKUP);
#use Bio::EnsEMBL::Utils::Exception qw(throw warning);
#use Bio::EnsEMBL::Variation::Utils::Sequence qw(hgvs_variant_notation format_hgvs_string get_3prime_seq_offset);
use consequence::Sequence qw(reverse_comp);
use consequence::VariationEffect qw(overlap within_cds within_intron stop_lost start_lost frameshift stop_retained);

use base qw(consequence::VariationFeatureOverlapAllele consequence::BaseTranscriptVariationAllele);
use Data::Dumper;

our $DEBUG = 0;
our $NO_TRANSFER = 0;

sub new_fast {
    my ($class, $hashref, $strong) = @_;

    #print Dumper $class;
    # swap a transcript_variation argument for a variation_feature_overlap one
    if ($hashref->{transcript_variation}) {
        $hashref->{variation_feature_overlap} = delete $hashref->{transcript_variation};
    }

    # and call the superclass

    return $class->SUPER::new_fast($hashref, $strong);
}

=head2 transcript_variation

  Description: Get/set the associated TranscriptVariation
  Returntype : Bio::EnsEMBL::Variation::TranscriptVariation
  Exceptions : throws if the argument is the wrong type
  Status     : Stable

=cut

sub transcript_variation {
    my ($self, $tv) = @_;
    assert_ref($tv, 'Bio::EnsEMBL::Variation::TranscriptVariation') if $Bio::EnsEMBL::Utils::Scalar::ASSERTIONS && $tv;
    return $self->variation_feature_overlap($tv);
}

=head2 variation_feature

  Description: Get the associated VariationFeature
  Returntype : Bio::EnsEMBL::Variation::VariationFeature
  Exceptions : none
  Status     : Stable

=cut

sub variation_feature {
    my $self = shift;
    return $self->transcript_variation->variation_feature;
}

=head2 affects_peptide

  Description: Check if this changes the resultant peptide sequence
  Returntype : boolean
  Exceptions : None
  Caller     : general
  Status     : At Risk

=cut

sub affects_peptide {
  my $self = shift;
  return scalar grep { $_->SO_term =~ /stop|missense|frameshift|inframe|initiator/ } @{$self->get_all_OverlapConsequences};
}

=head2 pep_allele_string

  Description: Return a '/' delimited string of the reference peptide and the
               peptide resulting from this allele, or a single peptide if this
               allele does not change the peptide (e.g. because it is synonymous)
  Returntype : string or undef if this allele is not in the CDS
  Exceptions : none
  Status     : Stable

=cut

sub pep_allele_string {
    my ($self) = @_;

    my $pep = $self->peptide;

    return undef unless $pep;

    my $ref_pep = $self->transcript_variation->get_reference_TranscriptVariationAllele->peptide;

    return undef unless $ref_pep;

    return $ref_pep ne $pep ? $ref_pep.'/'.$pep : $pep;
}

=head2 codon_allele_string

  Description: Return a '/' delimited string of the reference codon and the
               codon resulting from this allele
  Returntype : string or undef if this allele is not in the CDS
  Exceptions : none
  Status     : Stable

=cut

sub codon_allele_string {
    my ($self) = @_;

    my $codon = $self->codon;

    return undef unless $codon;

    my $ref_codon = $self->transcript_variation->get_reference_TranscriptVariationAllele->codon;

    return $ref_codon.'/'.$codon;
}

=head2 display_codon_allele_string

  Description: Return a '/' delimited string of the reference display_codon and the
               display_codon resulting from this allele. The display_codon identifies
               the nucleotides affected by this variant in UPPER CASE and other
               nucleotides in lower case
  Returntype : string or undef if this allele is not in the CDS
  Exceptions : none
  Status     : Stable

=cut

sub display_codon_allele_string {
    my ($self) = @_;

    my $display_codon = $self->display_codon;

    return undef unless $display_codon;

    my $ref_display_codon = $self->transcript_variation->get_reference_TranscriptVariationAllele->display_codon;

    return undef unless $ref_display_codon;

    return $ref_display_codon.'/'.$display_codon;
}

=head2 peptide

  Description: Return the amino acid sequence that this allele is predicted to result in
  Returntype : string or undef if this allele is not in the CDS or is a frameshift
  Exceptions : none
  Status     : Stable

=cut

sub peptide {
  my ($self, $peptide) = @_;

  $self->{peptide} = $peptide if $peptide;

  unless(exists($self->{peptide})) {


    #print Dumper $self;
    $self->{peptide} = undef;

    #return $self->{peptide} unless $self->seq_is_unambiguous_dna;

      my $codon = $self->codon;
      print("\n Test - codon -  ",$codon);
      # the codon method can set the peptide in some circumstances
      # so check here before we try an (expensive) translation
      return $self->{peptide} if $self->{peptide};

      my $tv = $self->base_variation_feature_overlap;

      # for mithocondrial dna we need to to use a different codon table
      my $codon_table = $tv->_codon_table;
      #print("\n Are we here",$codon_table);



      # translate the codon sequence to establish the peptide allele

      # allow for partial codons - split the sequence into whole and partial
      # e.g. AAAGG split into AAA and GG
      my $whole_codon   = substr($codon, 0, int(length($codon) / 3) * 3);
      my $partial_codon = substr($codon, int(length($codon) / 3) * 3);

      print($whole_codon);

      my $pep = '';

      if($whole_codon) {
          my $codon_seq = Bio::Seq->new(
            -seq        => $whole_codon,
            -moltype    => 'dna',
            -alphabet   => 'dna',
            );

          $pep .= $codon_seq->translate(undef, undef, undef, $codon_table)->seq;
        }

      # apply any seq edits?
      my $have_edits = 0;

      if($self->{is_reference}) {
        my $seq_edits = $tv->_seq_edits;

        if(scalar @$seq_edits) {

          # get TV coords, switch if necessary
          my ($tv_start, $tv_end) = ($tv->translation_start, $tv->translation_end);
          ($tv_start, $tv_end) = ($tv_end, $tv_start) if $tv_start > $tv_end;

          # get all overlapping seqEdits
          SE: foreach my $se(grep {overlap($tv_start, $tv_end, $_->start, $_->end)} @$seq_edits) {
            my ($se_start, $se_end, $alt) = ($se->start, $se->end, $se->alt_seq);
            my $se_alt_seq_length = length($alt);
            $have_edits = 1;

            # loop over each overlapping pos
            foreach my $tv_pos(grep {overlap($_, $_, $se_start, $se_end)} ($tv_start..$tv_end)) {

              # in some cases, the sequence edit can shorten the protein
              # this means our TV can fall outside the range of the edited protein
              # therefore for safety jump out
              if($tv_pos - $se_start >= $se_alt_seq_length) {
                return $self->{peptide} = undef;
              }

              # apply edit, adjusting for string position
              substr($pep, $tv_pos - $tv_start, 1) = substr($alt, $tv_pos - $se_start, 1);
            }
          }
        }
      }

      if($partial_codon && $pep ne '*') {
        $pep .= 'X';
      }

      $pep ||= '-';

      #$pep_cache->{$codon} = $pep if length($codon) <= 3 && !$have_edits;

      $self->{peptide} = $pep;

  }

  return $self->{peptide};
}

=head2 codon

  Description: Return the codon sequence that this allele is predicted to result in
  Returntype : string or undef if this allele is not in the CDS or is a frameshift
  Exceptions : none
  Status     : Stable

=cut

sub codon {
  my ($self, $codon) = @_;

  $self->{codon} = $codon if defined $codon;

  unless(exists($self->{codon})) {

    $self->{codon} = undef;

    my $tv = $self->base_variation_feature_overlap;
    #print Dumper $tv;
    #print("HERE-",$tv->translation_start);
    my ($tv_tr_start, $tv_tr_end) = ($tv->translation_start, $tv->translation_end);

    #print("HERE- START - ",$tv_tr_start,"\n END- ", $tv_tr_end,"\n");
    #unless($tv_tr_start && $tv_tr_end && $self->seq_is_dna) {
    #  return $self->{codon};
    #}

    # try to calculate the codon sequence
    my $seq = $self->feature_seq; #Originally this was feature_seq which was fetching variation seq not entire exon seq
    #print($seq);
    #print Dumper $tv->{'_cached_transcript'}->{'seq'};
    $seq = '' if $seq eq '-';

    # calculate necessary coords and lengths

    my $codon_cds_start = $tv_tr_start * 3 - 2;
    my $codon_cds_end   = $tv_tr_end * 3;
    my $codon_len       = $codon_cds_end - $codon_cds_start + 1;
    my $vf_nt_len       = $tv->cds_end - $tv->cds_start + 1;
    my $allele_len      = $self->seq_length;

    #print("codon_cds_start\t",$codon_cds_start,"\tcodon_cds_end\t",$codon_cds_end,"\t$codon_len\t","\t$vf_nt_len\t","\t$allele_len\t");
    my $cds;
    if ($allele_len != $vf_nt_len) {
      if (abs($allele_len - $vf_nt_len) % 3) {
        # this is a frameshift variation, we don't attempt to
        # calculate the resulting codon or peptide change as this
        # could get quite complicated
        # return undef;
      }

      ## Bioperl Seq object
      my $cds_obj = $self->_get_alternate_cds();
      $cds = $cds_obj->seq();
    }

    else {
      # splice the allele sequence into the CDS
      $cds = $tv->_translateable_seq;

      substr($cds, $tv->cds_start-1, $vf_nt_len) = $seq;
    }

    # and extract the codon sequence
    my $codon = substr($cds, $codon_cds_start-1, $codon_len + ($allele_len - $vf_nt_len));

    if (length($codon) < 1) {
      $self->{codon}   = '-';
      $self->{peptide} = '-';
    }
    else {
       $self->{codon} = $codon;
    }
  }

  return $self->{codon};
}

=head2 display_codon

  Description: Return the codon sequence that this allele is predicted to result in
               with the affected nucleotides identified in UPPER CASE and other
               nucleotides in lower case
  Returntype : string or undef if this allele is not in the CDS or is a frameshift
  Exceptions : none
  Status     : Stable

=cut

sub display_codon {
  my $self = shift;

  unless(exists($self->{_display_codon})) {

    # initialise so it doesn't get called again
    $self->{_display_codon} = undef;

    if(my $codon = $self->codon) {

      my $display_codon = lc $self->codon;

      if(my $codon_pos = $self->transcript_variation->codon_position) {

        # if this allele is an indel then just return all lowercase
        if ($self->feature_seq ne '-') {

          # codon_position is 1-based, while substr assumes the string starts at 0
          my $pos = $codon_pos - 1;

          my $len = length $self->feature_seq;

          substr($display_codon, $pos, $len) = uc substr($display_codon, $pos, $len);
        }
      }

      $self->{_display_codon} = $display_codon;
    }
  }

  return $self->{_display_codon};
}

=head2 polyphen_prediction

  Description: Return the qualitative PolyPhen-2 prediction for the effect of this allele.
               (Note that we currently only have PolyPhen predictions for variants that
               result in single amino acid substitutions in human)
  Returntype : string (one of 'probably damaging', 'possibly damaging', 'benign', 'unknown')
               if this is a missense change and a prediction is available, undef
               otherwise
  Exceptions : none
  Status     : At Risk

=cut

sub polyphen_prediction {
    my ($self, $classifier, $polyphen_prediction) = @_;

    $classifier ||= 'humvar';

    my $analysis = "polyphen_${classifier}";

    $self->{$analysis}->{prediction} = $polyphen_prediction if $polyphen_prediction;

    unless (defined $self->{$analysis}->{prediction}) {
        my ($prediction, $score) = $self->_protein_function_prediction($analysis);
        $self->{$analysis}->{score} = $score;
        $self->{$analysis}->{prediction} = $prediction;
    }

    return $self->{$analysis}->{prediction};
}

=head2 polyphen_score

  Description: Return the PolyPhen-2 probability that this allele is deleterious (Note that we
               currently only have PolyPhen predictions for variants that result in single
               amino acid substitutions in human)
  Returntype : float between 0 and 1 if this is a missense change and a prediction is
               available, undef otherwise
  Exceptions : none
  Status     : At Risk

=cut

sub polyphen_score {
    my ($self, $classifier, $polyphen_score) = @_;

    $classifier ||= 'humvar';

    my $analysis = "polyphen_${classifier}";

    $self->{$analysis}->{score} = $polyphen_score if defined $polyphen_score;

    unless (defined $self->{$analysis}->{score}) {
        my ($prediction, $score) = $self->_protein_function_prediction($analysis);
        $self->{$analysis}->{score} = $score;
        $self->{$analysis}->{prediction} = $prediction;
    }

    return $self->{$analysis}->{score};
}

=head2 sift_prediction

  Description: Return the qualitative SIFT prediction for the effect of this allele.
               (Note that we currently only have SIFT predictions for variants that
               result in single amino acid substitutions in human)
  Returntype : string (one of 'tolerated', 'deleterious') if this is a missense
               change and a prediction is available, undef otherwise
  Exceptions : none
  Status     : At Risk

=cut

sub sift_prediction {
    my ($self, $sift_prediction) = @_;

    $self->{sift_prediction} = $sift_prediction if $sift_prediction;

    unless (defined $self->{sift_prediction}) {
        my ($prediction, $score) = $self->_protein_function_prediction('sift');
        $self->{sift_score} = $score;
        $self->{sift_prediction} = $prediction unless $self->{sift_prediction};
    }

    return $self->{sift_prediction};
}

=head2 sift_score

  Description: Return the SIFT score for this allele (Note that we currently only have SIFT
               predictions for variants that result in single amino acid substitutions in human)
  Returntype : float between 0 and 1 if this is a missense change and a prediction is
               available, undef otherwise
  Exceptions : none
  Status     : At Risk

=cut

sub sift_score {
    my ($self, $sift_score) = @_;

    $self->{sift_score} = $sift_score if defined $sift_score;

    unless (defined $self->{sift_score}) {
        my ($prediction, $score) = $self->_protein_function_prediction('sift');
        $self->{sift_score} = $score;
        $self->{sift_prediction} = $prediction;
    }

    return $self->{sift_score};
}

=head2 cadd_prediction

  Description: Return the qualitative CADD prediction for the effect of this allele.
               (Note that we currently only have predictions for variants that
               result in single amino acid substitutions in human)
  Returntype : string (one of 'likely benign', 'likely deleterious') if this is a missense
               change and a prediction is available, undef otherwise. Predictions
               are assigned based on CADD PHRED scores. CADD PHRED scores greater or
               equal to 15 are considered likely deleterious.
  Exceptions : none
  Status     : At Risk

=cut

sub cadd_prediction {
  my ($self, $cadd_prediction) = @_;
  return $self->_prediction('cadd_prediction', $cadd_prediction);
}

=head2 dbnsfp_revel_prediction

  Description: Return the qualitative REVEL prediction for the effect of this allele.
               (Note that we currently only have predictions for variants that
               result in single amino acid substitutions in human)
  Returntype : string (one of 'likely_disease_causing', 'likely_not_disease_causing')
               if this is a missense change and a prediction is available, undef otherwise.
               We chose 0.5 as the threshold to assign the predictions. From the REVEL paper:
               For example, 75.4% of disease mutations but only 10.9% of neutral variants
               have a REVEL score above 0.5, corresponding to a sensitivity of 0.754 and
               specificity of 0.891.
  Exceptions : none
  Status     : At Risk

=cut

sub dbnsfp_revel_prediction {
  my ($self, $dbnsfp_revel_prediction) = @_;
  return $self->_prediction('dbnsfp_revel_prediction', $dbnsfp_revel_prediction);
}

=head2 dbnsfp_meta_lr_prediction

  Description: Return the qualitative MetaLR prediction for the effect of this allele.
               (Note that we currently only have predictions for variants that
               result in single amino acid substitutions in human)
  Returntype : string (one of 'tolerated', 'damaging').
               The score cutoff between "D" and "T" is 0.5.
  Exceptions : none
  Status     : At Risk

=cut

sub dbnsfp_meta_lr_prediction {
  my ($self, $dbnsfp_meta_lr_prediction) = @_;
  return $self->_prediction('dbnsfp_meta_lr_prediction', $dbnsfp_meta_lr_prediction);
}

=head2 dbnsfp_mutation_assessor_prediction

  Description: Return the qualitative MutationAssessor prediction for the effect of this allele.
               (Note that we currently only have predictions for variants that
               result in single amino acid substitutions in human)
  Returntype : string (one of 'high', 'medium', 'low', 'neutral').
  Exceptions : none
  Status     : At Risk

=cut

sub dbnsfp_mutation_assessor_prediction {
  my ($self, $dbnsfp_mutation_assessor_prediction) = @_;
  return $self->_prediction('dbnsfp_mutation_assessor_prediction', $dbnsfp_mutation_assessor_prediction);
}

=head2 _prediction

  Description: Return prediction for specified score type.
  Returntype : float
  Exceptions : none
  Status     : At Risk

=cut

sub _prediction {
  my ($self, $prediction_type, $prediction) = @_;
  $self->{$prediction_type} = $prediction if $prediction;

  unless (defined $self->{$prediction_type}) {
    my $analysis = $prediction_type;
    $analysis =~ s/_prediction//;
    my ($prediction, $score) = $self->_protein_function_prediction($analysis);
    my $score_type = $prediction_type;
    $score_type =~ s/_prediction/_score/;
    $self->{$score_type} = $score;
    $self->{$prediction_type} = $prediction;
  }
  return $self->{$prediction_type};
}

=head2 cadd_score

  Description: Return the CADD PHRED score for this allele.
  Returntype : float if this is a missense change and a prediction is available, undef otherwise
  Exceptions : none
  Status     : At Risk

=cut

sub cadd_score {
  my ($self, $cadd_score) = @_;
  return $self->_score('cadd_score');
}

=head2 dbnsfp_revel_score

  Description: Return the REVEL score for this allele. The score is retrieved from dbNSFP. (We only
               have predictions for variants that result in single amino acid substitutions in human)
  Returntype : float between 0 and 1 if this is a missense change and a prediction is
               available, undef otherwise
  Exceptions : none
  Status     : At Risk

=cut

sub dbnsfp_revel_score {
  my ($self, $dbnsfp_revel_score) = @_;
  return $self->_score('dbnsfp_revel_score');
}

=head2 dbnsfp_meta_lr_score

  Description: Return the MetaLR score for this allele. The score is retrieved from dbNSFP. (We only
               have predictions for variants that result in single amino acid substitutions in human)
  Returntype : float if this is a missense change and a prediction is
               available, undef otherwise
  Exceptions : none
  Status     : At Risk

=cut

sub dbnsfp_meta_lr_score {
  my ($self, $dbnsfp_meta_lr_score) = @_;
  return $self->_score('dbnsfp_meta_lr_score', $dbnsfp_meta_lr_score);
}

=head2 dbnsfp_mutation_assessor_score

  Description: Return the MutationAssessor score for this allele. The score is retrieved from dbNSFP. (We only
               have predictions for variants that result in single amino acid substitutions in human)
  Returntype : float if this is a missense change and a prediction is
               available, undef otherwise
  Exceptions : none
  Status     : At Risk

=cut

sub dbnsfp_mutation_assessor_score {
  my ($self, $dbnsfp_mutation_assessor_score) = @_;
  return $self->_score('dbnsfp_mutation_assessor_score', $dbnsfp_mutation_assessor_score);
}


=head2 _score

  Description: Return score for specified score type.
  Returntype : float
  Exceptions : none
  Status     : At Risk

=cut

sub _score {
  my ($self, $score_type, $score) = @_;
  $self->{$score_type} = $score if defined $score;

  unless (defined $self->{$score_type}) {
      my $analysis = $score_type;
      $analysis =~ s/_score//;
      my ($prediction, $score) = $self->_protein_function_prediction($analysis);
      my $prediction_type = $score_type;
      $prediction_type =~ s/_score/_prediction/;
      $self->{$score_type} = $score;
      $self->{$prediction_type} = $prediction;
  }
  return $self->{$score_type};
}

sub _protein_function_prediction {
    my ($self, $analysis) = @_;

    # we can only get results for variants that cause a single amino acid substitution,
    # so check the peptide allele string first

    if ($self->pep_allele_string && $self->pep_allele_string =~ /^[A-Z]\/[A-Z]$/ && defined $AA_LOOKUP->{$self->peptide}) {
        if (my $matrix = $self->transcript_variation->_protein_function_predictions($analysis)) {

            # temporary fix - check $matrix is not an empty hashref
            if(ref($matrix) && ref($matrix) eq 'Bio::EnsEMBL::Variation::ProteinFunctionPredictionMatrix') {

                my ($prediction, $score) = $matrix->get_prediction(
                    $self->transcript_variation->translation_start,
                    $self->peptide,
                );

                return wantarray ? ($prediction, $score) : $prediction;
            }
        }
    }

    return undef;
}

sub _get_alternate_cds{

  my $self = shift;
  #print Dumper $self->transcript_variation;
  ### get reference sequence
  my $reference_cds_seq = $self->transcript_variation->_translateable_seq();
  #print Dumper $reference_cds_seq;
  my $tv = $self->transcript_variation;
  my $vf = $tv->variation_feature;
  my $tr = $tv->transcript;

  return undef unless defined($tv->cds_start) && defined($tv->cds_end());

  ### get sequences upstream and downstream of variant
  my $upstream_seq   =  substr($reference_cds_seq, 0, ($tv->cds_start() -1) );
  my $downstream_seq =  substr($reference_cds_seq, ($tv->cds_end() ) );

  ### fix alternate allele if deletion or on opposite strand
  my $alt_allele  = $self->variation_feature_seq();
  $alt_allele  =~ s/\-//;
  if($alt_allele && $vf->strand() != $tr->strand()){
    reverse_comp(\$alt_allele) ;
  }

  ### build alternate seq
  my $alternate_seq  = $upstream_seq . $alt_allele . $downstream_seq ;
  $alternate_seq  = $self->_trim_incomplete_codon($alternate_seq );

  ### create seq obj with alternative allele in the CDS sequence
  my $alt_cds =Bio::PrimarySeq->new(-seq => $alternate_seq,  -id => 'alt_cds', -alphabet => 'dna');

  ### append UTR if available as stop may be disrupted
  my $utr = $self->transcript_variation->_three_prime_utr();

  if (defined $utr) {
  ### append the UTR to the alternative CDS
    $alt_cds->seq($alt_cds->seq() . $utr->seq());
  }
  else{
   ##warn "No UTR available for alternate CDS\n";
  }

  return $alt_cds;
}

# same for $transcript->feature_Slice
# need to be careful here in case the transcript has moved slice
# you never know!
sub _transcript_feature_Slice {
  my ($self, $tr) = @_;

  my $fc = $tr->{_variation_effect_feature_cache} ||= {};

  # check that we haven't moved slice
  my $curr_slice_ref = sprintf('%s', $tr->slice());
  my $prev_slice_ref = $fc->{slice_ref};

  if(
    !exists($fc->{feature_Slice}) ||
    $fc->{slice_ref} && $fc->{slice_ref} ne $curr_slice_ref
  ) {

    # log the reference of this slice
    $fc->{slice_ref} = $curr_slice_ref;
    $fc->{feature_Slice} = $tr->feature_Slice();
  }

  return $fc->{feature_Slice};
}


1;
