=head1 LICENSE

Copyright [1999-2015] Wellcome Trust Sanger Institute and the EMBL-European Bioinformatics Institute
Copyright [2016-2019] EMBL-European Bioinformatics Institute

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

     http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
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

Bio::EnsEMBL::Variation::TranscriptVariation

=head1 SYNOPSIS

    use Bio::EnsEMBL::Variation::TranscriptVariation;

    my $tv = Bio::EnsEMBL::Variation::TranscriptVariation->new(
        -transcript        => $transcript,
        -variation_feature => $var_feat
    );

    print "consequence type: ", (join ",", @{$tv->consequence_type}), "\n";
    print "cdna coords: ", $tv->cdna_start, '-', $tv->cdna_end, "\n";
    print "cds coords: ", $tv->cds_start, '-', $tv->cds_end, "\n";
    print "pep coords: ", $tv->translation_start, '-',$tv->translation_end, "\n";
    print "amino acid change: ", $tv->pep_allele_string, "\n";
    print "codon change: ", $tv->codons, "\n";
    print "allele sequences: ", (join ",", map { $_->variation_feature_seq }
        @{ $tv->get_all_TranscriptVariationAlleles }), "\n";

=head1 DESCRIPTION

A TranscriptVariation object represents a variation feature which is in close
proximity to an Ensembl transcript. A TranscriptVariation object has several
attributes which define the relationship of the variation to the transcript.

=cut

package consequence::TranscriptVariation;

use strict;
use warnings;

#use Bio::EnsEMBL::Utils::Scalar qw(assert_ref check_ref);
#use Bio::EnsEMBL::Utils::Sequence qw(reverse_comp);
#use Bio::EnsEMBL::Variation::TranscriptVariationAllele;
use consequence::VariationEffect qw(overlap within_cds);
#use Bio::EnsEMBL::Variation::BaseTranscriptVariation;

use base qw(consequence::BaseTranscriptVariation consequence::VariationFeatureOverlap);

=head2 new

  Arg [-TRANSCRIPT] :
    The Bio::EnsEMBL::Transcript associated with the given VariationFeature

  Arg [-VARIATION_FEATURE] :
    The Bio::EnsEMBL::VariationFeature associated with the given Transcript

  Arg [-ADAPTOR] :
    A Bio::EnsEMBL::Variation::DBSQL::TranscriptVariationAdaptor

  Arg [-DISAMBIGUATE_SINGLE_NUCLEOTIDE_ALLELES] :
    A flag indiciating if ambiguous single nucleotide alleles should be disambiguated
    when constructing the TranscriptVariationAllele objects, e.g. a Variationfeature
    with an allele string like 'T/M' would be treated as if it were 'T/A/C'. We limit
    ourselves to single nucleotide alleles to avoid the combinatorial explosion if we
    allowed longer alleles with potentially many ambiguous bases.

  Example :
    my $tv = Bio::EnsEMBL::Variation::TranscriptVariation->new(
        -transcript        => $transcript,
        -variation_feature => $var_feat
    );

  Description: Constructs a new TranscriptVariation instance given a VariationFeature
               and a Transcript, most of the work is done in the VariationFeatureOverlap
               superclass - see there for more documentation.
  Returntype : A new Bio::EnsEMBL::Variation::TranscriptVariation instance
  Exceptions : throws unless both VARIATION_FEATURE and TRANSCRIPT are supplied
  Status     : Stable

=cut

sub new {
    my $class = shift;

    my %args = @_;

    # swap a '-transcript' argument for a '-feature' one for the superclass
    unless($args{'-feature'} ||= delete $args{'-transcript'}) {
      for my $arg (keys %args) {
        if (lc($arg) eq '-transcript') {
          $args{'-feature'} = delete $args{$arg};
        }
      }
    }

    # call the superclass constructor
    my $self = $class->SUPER::new(%args) || return undef;

    # rebless the alleles from vfoas to tvas
    map { bless $_, 'consequence::TranscriptVariationAllele' }
        @{ $self->get_all_BaseVariationFeatureOverlapAlleles };

    return $self;
}


=head2 get_all_alternate_TranscriptVariationAlleles

  Description: Get a list of the alternate alleles of this TranscriptVariation
  Returntype : listref of Bio::EnsEMBL::Variation::TranscriptVariationAllele objects
  Exceptions : none
  Status     : Stable

=cut

sub get_all_alternate_TranscriptVariationAlleles {
    my $self = shift;
    return $self->SUPER::get_all_alternate_VariationFeatureOverlapAlleles(@_);
}



1;
