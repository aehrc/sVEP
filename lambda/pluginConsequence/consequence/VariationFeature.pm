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

Bio::EnsEMBL::Variation::VariationFeature - A genomic position for a nucleotide variation.

=head1 SYNOPSIS

    # Variation feature representing a single nucleotide polymorphism
    $vf = Bio::EnsEMBL::Variation::VariationFeature->new
       (-start   => 100,
        -end     => 100,
        -strand  => 1,
        -slice   => $slice,
        -allele_string => 'A/T',
        -variation_name => 'rs635421',
        -map_weight  => 1,
        -variation => $v);

    # Variation feature representing a 2bp insertion
    $vf = Bio::EnsEMBL::Variation::VariationFeature->new
       (-start   => 1522,
        -end     => 1521, # end = start-1 for insert
        -strand  => -1,
        -slice   => $slice,
        -allele_string => '-/AA',
        -variation_name => 'rs12111',
        -map_weight  => 1,
        -variation => $v2);

    ...

    # a variation feature is like any other ensembl feature, can be
    # transformed etc.
    $vf = $vf->transform('supercontig');

    print $vf->start(), "-", $vf->end(), '(', $vf->strand(), ')', "\n";

    print $vf->name(), ":", $vf->allele_string();

    # Get the Variation object which this feature represents the genomic
    # position of. If not already retrieved from the DB, this will be
    # transparently lazy-loaded
    my $v = $vf->variation();

=head1 DESCRIPTION

This is a class representing the genomic position of a nucleotide variation
from the ensembl-variation database.  The actual variation information is
represented by an associated Bio::EnsEMBL::Variation::Variation object. Some
of the information has been denormalized and is available on the feature for
speed purposes.  A VariationFeature behaves as any other Ensembl feature.
See B<Bio::EnsEMBL::Feature> and B<Bio::EnsEMBL::Variation::Variation>.

=head1 METHODS

=cut

use strict;
use warnings;

package consequence::VariationFeature;

use Scalar::Util qw(weaken isweak);
use Data::Dumper;

use consequence::BaseVariationFeature;
use consequence::Exception qw(throw warning);
#use Bio::EnsEMBL::Utils::Scalar qw(assert_ref);
use consequence::Argument  qw(rearrange);
use consequence::Sequence qw(reverse_comp expand);
#use Bio::EnsEMBL::Variation::Utils::Sequence qw(ambiguity_code hgvs_variant_notation SO_variation_class format_hgvs_string get_3prime_seq_offset trim_right);
#use Bio::EnsEMBL::Variation::Utils::Sequence;
#use Bio::EnsEMBL::Variation::Variation;
use consequence::VariationEffect qw(MAX_DISTANCE_FROM_TRANSCRIPT);
use consequence::Constants qw($DEFAULT_OVERLAP_CONSEQUENCE %VARIATION_CLASSES);
#use Bio::EnsEMBL::Variation::RegulatoryFeatureVariation;
#use Bio::EnsEMBL::Variation::MotifFeatureVariation;
#use Bio::EnsEMBL::Variation::ExternalFeatureVariation;
#use Bio::EnsEMBL::Variation::IntergenicVariation;
#use Bio::EnsEMBL::Slice;
#use Bio::EnsEMBL::Variation::DBSQL::TranscriptVariationAdaptor;
#use Bio::PrimarySeq;
#use Bio::SeqUtils;
#use Bio::EnsEMBL::Variation::Utils::Sequence  qw(%EVIDENCE_VALUES);


our @ISA = ('consequence::BaseVariationFeature');

our $DEBUG = 0;
=head2 new

  Arg [-dbID] :
    see superclass constructor

  Arg [-ADAPTOR] :
    see superclass constructor

  Arg [-START] :
    see superclass constructor
  Arg [-END] :
    see superclass constructor

  Arg [-STRAND] :
    see superclass constructor

  Arg [-SLICE] :
    see superclass constructor

  Arg [-ALLELE_STRING] :
    string - the different alleles found for this variant at this feature location

  Arg [-ANCESTRAL_ALLELE] :
    string - the ancestral allele for this variation feature

  Arg [-VARIATION_NAME] :
    string - the name of the variant this feature is for (denormalisation
    from Variation object).

  Arg [-MAP_WEIGHT] :
    int - the number of times that the variant associated with this feature
    has hit the genome. If this was the only feature associated with this
    variation_feature the map_weight would be 1.

  Arg [-VARIATION] :
    int - the variation object associated with this feature.

  Arg [-SOURCE] :
    object ref - the source object describing where the variant comes from.

  Arg [-EVIDENCE] :
     reference to list of strings

  Arg [-OVERLAP_CONSEQUENCES] :
     listref of Bio::EnsEMBL::Variation::OverlapConsequences - all the consequences of this VariationFeature

  Arg [-VARIATION_ID] :
    int - the internal id of the variation object associated with this
    identifier. This may be provided instead of a variation object so that
    the variation may be lazy-loaded from the database on demand.

  Example    :
    $vf = Bio::EnsEMBL::Variation::VariationFeature->new(
        -start   => 100,
        -end     => 100,
        -strand  => 1,
        -slice   => $slice,
        -allele_string => 'A/T',
        -variation_name => 'rs635421',
        -map_weight  => 1,
	      -source  => 'dbSNP',
        -variation => $v
    );

  Description : Constructor. Instantiates a new VariationFeature object.
  Returntype  : Bio::EnsEMBL::Variation::Variation
  Exceptions  : none
  Caller      : general
  Status      : Stable

=cut

sub new {
  my $caller = shift;
  my $class = ref($caller) || $caller;

  my $self = $class->SUPER::new(@_);

  my (
      $allele_str,
      $ancestral_allele,
      $var_name,
      $map_weight,
      $variation,
      $variation_id,
      $source_id,
      $source,
      $is_somatic,
      $overlap_consequences,
      $class_so_term,
      $minor_allele,
      $minor_allele_freq,
      $minor_allele_count,
      $evidence,
      $clin_sig,
      $display
  ) = rearrange([qw(
          ALLELE_STRING
          ANCESTRAL_ALLELE
          VARIATION_NAME
          MAP_WEIGHT
          VARIATION
          _VARIATION_ID
          _SOURCE_ID
          SOURCE
          IS_SOMATIC
          OVERLAP_CONSEQUENCES
          CLASS_SO_TERM
          MINOR_ALLELE
          MINOR_ALLELE_FREQUENCY
          MINOR_ALLELE_COUNT
          EVIDENCE
          CLINICAL_SIGNIFICANCE
          DISPLAY
        )], @_);

  $self->{'allele_string'}          = $allele_str;
  $self->{'ancestral_allele'}       = $ancestral_allele;
  $self->{'variation_name'}         = $var_name;
  $self->{'map_weight'}             = $map_weight;
  $self->{'variation'}              = $variation;
  $self->{'_variation_id'}          = $variation_id;
  $self->{'_source_id'}             = $source_id;
  $self->{'source'}                 = $source;
  $self->{'is_somatic'}             = $is_somatic;
  $self->{'overlap_consequences'}   = $overlap_consequences;
  $self->{'class_SO_term'}          = $class_so_term;
  $self->{'minor_allele'}           = $minor_allele;
  $self->{'minor_allele_frequency'} = $minor_allele_freq;
  $self->{'minor_allele_count'}     = $minor_allele_count;
  $self->{'evidence'}               = $evidence;
  $self->{'clinical_significance'}  = $clin_sig;
  $self->{'display'}                = $display;
  return $self;
}



sub new_fast {

  my $class = shift;
  my $hashref = shift;
  my $self = bless $hashref, $class;
  #weaken($self->{'adaptor'})  if ( ! isweak($self->{'adaptor'}) );
  return $self;

}


=head2 allele_string

  Arg [1]     : string $newval (optional)
                The new value to set the allele_string attribute to
  Arg [2]     : int $strand (optional)
                Strand on which to report alleles (default is $obj->strand)
  Example     : $allele_string = $obj->allele_string()
  Description : Getter/Setter for the allele_string attribute.
                The allele_string is a '/' demimited string representing the
                alleles associated with this features variation.
  Returntype  : string
  Exceptions  : none
  Caller      : general
  Status      : Stable

=cut

sub add_TranscriptVariation {
    my ($self, $tv) = @_;
    #print Dumper $tv->{feature};


    my  $tr_stable_id = $tv->{feature}->{stable_id};


    $self->{transcript_variations}->{$tr_stable_id} = $tv;
}


sub strand {
  my ($self, $value ) = @_;

  if( defined $value ) {
    $self->{'strand'} = $value;
  }

  return $self->{'strand'};
}
sub exon {
  my ($self, $value ) = @_;

  if( defined $value ) {
    $self->{'exon'} = $value;
  }

  return $self->{'exon'};
}
sub intron {
  my ($self, $value ) = @_;

  if( defined $value ) {
    $self->{'intron'} = $value;
  }

  return $self->{'intron'};
}

sub get_all_TranscriptVariations {

    my ($self, $transcripts) = @_;

    if ($transcripts) {
        assert_ref($transcripts, 'ARRAY');
        map { assert_ref($_, 'consequence::Transcript') } @$transcripts;
    }



    if ($transcripts) {
        # just return TranscriptVariations for the requested Transcripts
        return [
          map {
            $self->{transcript_variations}->{$self->_get_transcript_key($_)} ||
            $self->{transcript_variations}->{$_->stable_id}
          } @$transcripts
        ];
    }
    else {
        # return all TranscriptVariations
        return [ map {$self->{transcript_variations}->{$_}} sort keys %{$self->{transcript_variations}} ];
    }
}

sub allele_string{
  my $self = shift;
  my $newval = shift;
  my $strand = shift;

  if(defined($newval)) {
	 $self->{allele_string} = $newval;
   delete($self->{_ref_allele});
   delete($self->{_alt_alleles});
   return $self->{allele_string};
  }

  my $as = $self->{'allele_string'};

  if(defined($strand) && $strand != $self->strand) {
	my @flipped;

	foreach my $a(split /\//, $as) {
	  reverse_comp(\$a) if $a =~ /^[ACGTn\-]+$/;
	  push @flipped, $a;
	}

	$as = join '/', @flipped;
  }

  return $as;
}

sub seq_region_start {
  my ($self, $value ) = @_;

  if( defined $value ) {
    $self->{'seq_region_start'} = $value;
  }

  return $self->{'seq_region_start'};
}

sub seq_region_end {
  my ($self, $value ) = @_;

  if( defined $value ) {
    $self->{'seq_region_end'} = $value;
  }

  return $self->{'seq_region_end'};
}




1;
