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

Bio::EnsEMBL::Transcript - object representing an Ensembl transcript

=head1 SYNOPSIS

Creation:

  my $tran = new Bio::EnsEMBL::Transcript();
  my $tran = new Bio::EnsEMBL::Transcript( -EXONS => \@exons );

Manipulation:

  # Returns an array of Exon objects
  my @exons = @{ $tran->get_all_Exons() };

  # Returns the peptide translation of the exons as a Bio::Seq
  if ( $tran->translation() ) {
    my $pep = $tran->translate();
  } else {
    print "Transcript ", $tran->stable_id(), " is non-coding\n";
  }

=head1 DESCRIPTION

A representation of a transcript within the Ensembl system.  A transcript
consists of a set of Exons and (possibly) a Translation which defines the
coding and non-coding regions of the exons.

=cut

package consequence::Transcript;

use strict;

#use Bio::EnsEMBL::Feature;
#use Bio::EnsEMBL::UTR;
#use Bio::EnsEMBL::Intron;
#use Bio::EnsEMBL::ExonTranscript;
#use Bio::EnsEMBL::CDS;
use consequence::TranscriptMapper;
#use Bio::EnsEMBL::SeqEdit;
#use Bio::EnsEMBL::Biotype;
#use Bio::EnsEMBL::Utils::Argument qw( rearrange );
#use Bio::EnsEMBL::Utils::Exception qw(warning throw );
#use Bio::EnsEMBL::Utils::Scalar qw( assert_ref );

#use parent qw(Bio::EnsEMBL::Feature);

use constant SEQUENCE_ONTOLOGY => {
  acc  => 'SO:0000673',
  term => 'transcript',
};

=head2 new

  Arg [-EXONS] :
        reference to list of Bio::EnsEMBL::Exon objects - exons which make up
        this transcript
  Arg [-STABLE_ID] :
        string - the stable identifier of this transcript
  Arg [-VERSION] :
        int - the version of the stable identifier of this transcript
  Arg [-EXTERNAL_NAME] :
        string - the external database name associated with this transcript
  Arg [-EXTERNAL_DB] :
        string - the name of the database the external name is from
  Arg [-EXTERNAL_STATUS]:
        string - the status of the external identifier
  Arg [-DISPLAY_XREF]:
        Bio::EnsEMBL::DBEntry - The external database entry that is used
        to label this transcript when it is displayed.
  Arg [-CREATED_DATE]:
        string - the date the transcript was created
  Arg [-MODIFIED_DATE]:
        string - the date the transcript was last modified
  Arg [-DESCRIPTION]:
        string - the transcripts description
  Arg [-BIOTYPE]:
        string - the biotype e.g. "protein_coding"
  Arg [-IS_CURRENT]:
        Boolean - specifies if this is the current version of the transcript
  Arg [-SOURCE]:
        string - the transcript source, e.g. "ensembl"

  Example    : $tran = new Bio::EnsEMBL::Transcript(-EXONS => \@exons);
  Description: Constructor. Instantiates a Transcript object.
  Returntype : Bio::EnsEMBL::Transcript
  Exceptions : throw on bad arguments
  Caller     : general
  Status     : Stable

=cut

sub new {
  my $proto = shift;

  my $class = ref($proto) || $proto;

  my $self = $class->SUPER::new(@_);

  my (
    $exons,            $stable_id,    $version,
    $external_name,    $external_db,  $external_status,
    $display_xref,     $created_date, $modified_date,
    $description,      $biotype,      $confidence,
    $external_db_name, $is_current,
    $source
  );

    (
      $exons,            $stable_id,    $version,
      $external_name,    $external_db,  $external_status,
      $display_xref,     $created_date, $modified_date,
      $description,      $biotype,      $confidence,
      $external_db_name, $is_current,
      $source
      )
      = rearrange( [
        'EXONS',            'STABLE_ID',
        'VERSION',          'EXTERNAL_NAME',
        'EXTERNAL_DB',      'EXTERNAL_STATUS',
        'DISPLAY_XREF',     'CREATED_DATE',
        'MODIFIED_DATE',    'DESCRIPTION',
        'BIOTYPE',          'CONFIDENCE',
        'EXTERNAL_DB_NAME',
        'IS_CURRENT',       'SOURCE'
      ],
      @_
      );

  $self->{'stable_id'}          = $stable_id;
  $self->{'version'}       = $version;
  $self->{'external_name'}         = $external_name;
  $self->{'source'}             = $source;
  $self->{'biotype'}              = $biotype;
  $self->{'confidence'}          = $confidence;


  return $self;
} ## end sub new

sub new_fast {

  my $class = shift;
  my $hashref = shift;
  my $self = bless $hashref, $class;
  #weaken($self->{'adaptor'})  if ( ! isweak($self->{'adaptor'}) );
  return $self;

}

sub translation {
  my ( $self, $translation ) = @_;

  if ( defined($translation) ) {
    #assert_ref( $translation, 'Bio::EnsEMBL::Translation' );

    $self->{'translation'} = $translation;
    $translation->transcript($self);

    $self->{'cdna_coding_start'} = undef;
    $self->{'cdna_coding_end'}   = undef;

    $self->{'coding_region_start'} = undef;
    $self->{'coding_region_end'}   = undef;

    $self->{'transcript_mapper'} = undef;

  } elsif ( @_ > 1 ) {
    if ( defined( $self->{'translation'} ) ) {
      # Removing existing translation

      $self->{'translation'}->transcript(undef);
      delete( $self->{'translation'} );

      $self->{'cdna_coding_start'} = undef;
      $self->{'cdna_coding_end'}   = undef;

      $self->{'coding_region_start'} = undef;
      $self->{'coding_region_end'}   = undef;

      $self->{'transcript_mapper'} = undef;
    }
  }

  return $self->{'translation'};
} ## end sub translation

sub cdna_coding_start {
  my $self = shift;

  if( @_ ) {
    $self->{'cdna_coding_start'} = shift;
  }

  if(!defined $self->{'cdna_coding_start'} && defined $self->translation){

    #print("\n##################HERE#################\n");
    # calc coding start relative from the start of translation (in cdna coords)
    my $start = 0;

    my @exons = @{$self->get_all_Exons};
    my $exon;

    while($exon = shift @exons) {
      if($exon == $self->translation->start_Exon) {
        #add the utr portion of the start exon
        $start += $self->translation->start;
        last;
      } else {
        #add the entire length of this non-coding exon
        $start += $exon->length;
      }
    }

    # adjust cdna coords if sequence edits are enabled
    if($self->edits_enabled()) {
      my @seqeds = @{$self->get_all_SeqEdits()};
      if (scalar @seqeds) {
        my $transl_start = $self->get_all_Attributes('_transl_start');
        if (@{$transl_start}) {
          $start = $transl_start->[0]->value;
        } else {
          # sort in reverse order to avoid adjustment of downstream edits
          @seqeds = sort {$b->start() <=> $a->start()} @seqeds;

          foreach my $se (@seqeds) {
            # use less than start so that start of CDS can be extended
            if($se->start() < $start) {
              $start += $se->length_diff();
            }
          }
        }
      }
    }

    $self->{'cdna_coding_start'} = $start;
  }

  return $self->{'cdna_coding_start'};
}

sub cdna_coding_end {
  my $self = shift;

  if( @_ ) {
    $self->{'cdna_coding_end'} = shift;
  }

  if(!defined $self->{'cdna_coding_end'} && defined $self->translation) {
    my @exons = @{$self->get_all_Exons};

    my $end = 0;
    while(my $exon = shift @exons) {
      if($exon == $self->translation->end_Exon) {
        # add coding portion of the final coding exon
        $end += $self->translation->end;
        last;
      } else {
        # add entire exon
        $end += $exon->length;
      }
    }

    # adjust cdna coords if sequence edits are enabled
    if($self->edits_enabled()) {
      my @seqeds = @{$self->get_all_SeqEdits()};
      if (scalar @seqeds) {
        my $transl_end = $self->get_all_Attributes('_transl_end');
        if (@{$transl_end}) {
          $end = $transl_end->[0]->value;
        } else {
          # sort in reverse order to avoid adjustment of downstream edits
          @seqeds = sort {$b->start() <=> $a->start()} @seqeds;

          foreach my $se (@seqeds) {
            # use less than or equal to end+1 so end of the CDS can be extended
            if($se->start() <= $end + 1) {
              $end += $se->length_diff();
            }
          }
        }
      }
    }

    $self->{'cdna_coding_end'} = $end;
  }

  return $self->{'cdna_coding_end'};
}




sub translateable_seq {
  my ( $self ) = @_;

  if ( !$self->translation() ) {
    return '';
  }

  my $mrna = $self->spliced_seq();

  my $start = $self->cdna_coding_start();
  my $end   = $self->cdna_coding_end();

  $mrna = substr( $mrna, $start - 1, $end - $start + 1 );

  my $start_phase = $self->translation->start_Exon->phase();
  if( $start_phase > 0 ) {
    $mrna = "N"x$start_phase . $mrna;
  }
  if( ! $start || ! $end ) {
    return "";
  }

  return $mrna;
}

sub seq_region_start {
  my ($self, $value) = @_;

  if( defined $value ) {
    $self->{'seq_region_start'} = $value;
  } elsif(!defined $self->{'seq_region_start'} &&
    defined $self->translation) {
    #calculate the coding start from the translation
    my $start;
    my $strand = $self->translation()->start_Exon->strand();
    if( $strand == 1 ) {
      $start = $self->translation()->start_Exon->start();
      $start += ( $self->translation()->start() - 1 );
    } else {
      $start = $self->translation()->end_Exon->end();
      $start -= ( $self->translation()->end() - 1 );
    }
    $self->{'seq_region_start'} = $start;
  }

  return $self->{'seq_region_start'};
}


=head2 coding_region_end

  Arg [1]    : (optional) $value
  Example    : $coding_region_end = $transcript->coding_region_end
  Description: Retrieves the end of the coding region of this transcript
               in genomic coordinates (i.e. in either slice or contig coords).
               By convention, the coding_region_end is always higher than the
               value returned by the coding_region_start method.
               The value returned by this function is NOT the biological
               coding end since on the reverse strand the biological coding
               end would be the lower genomic value.

               This function will return undef if this is a pseudogene
               (a non-translated transcript).
  Returntype : int
  Exceptions : none
  Caller     : general
  Status     : Stable

=cut

sub seq_region_end {
  my ($self, $value ) = @_;

  my $strand;
  my $end;

  if( defined $value ) {
    $self->{'seq_region_end'} = $value;
  } elsif( ! defined $self->{'seq_region_end'}
     && defined $self->translation() ) {
    $strand = $self->translation()->start_Exon->strand();
    if( $strand == 1 ) {
      $end = $self->translation()->end_Exon->start();
      $end += ( $self->translation()->end() - 1 );
    } else {
      $end = $self->translation()->start_Exon->end();
      $end -= ( $self->translation()->start() - 1 );
    }
    $self->{'seq_region_end'} = $end;
  }

  return $self->{'seq_region_end'};
}

sub seq_length {
  my ($self, $value ) = @_;

  if( defined $value ) {
    $self->{'seq_length'} = $value;
  }

  return $self->{'seq_length'};
}

sub strand {
  my ($self, $value ) = @_;

  if( defined $value ) {
    $self->{'strand'} = $value;
  }

  return $self->{'strand'};
}

sub seq {
  my ($self, $value ) = @_;

  if( defined $value ) {
    $self->{'seq'} = $value;
  }

  return $self->{'seq'};
}

sub cds_frame {
  my ($self, $value ) = @_;

  if( defined $value ) {
    $self->{'cds_frame'} = $value;
  }

  return $self->{'cds_frame'};
}

sub stable_id {
  my ($self, $value ) = @_;

  if( defined $value ) {
    $self->{'stable_id'} = $value;
  }

  return $self->{'stable_id'};
}


sub get_TranscriptMapper {
  my ( $self ) = @_;
  return $self->{'transcript_mapper'} ||=
    consequence::TranscriptMapper->new($self);
}

sub seq {
  my ($self) = @_;

  return
    Bio::Seq->new( -id       => $self->stable_id,
                   -moltype  => 'dna',
                   -alphabet => 'dna',
                   -seq      => $self->seq );
}


=head2 pep2genomic

  Description: See Bio::EnsEMBL::TranscriptMapper::pep2genomic

=cut

sub pep2genomic {
  my $self = shift;
  return $self->get_TranscriptMapper()->pep2genomic(@_);
}


=head2 genomic2pep

  Description: See Bio::EnsEMBL::TranscriptMapper::genomic2pep

=cut

sub genomic2pep {
  my $self = shift;
  return $self->get_TranscriptMapper()->genomic2pep(@_);
}


=head2 cdna2genomic

  Description: See Bio::EnsEMBL::TranscriptMapper::cdna2genomic

=cut

sub cdna2genomic {
  my $self = shift;
  return $self->get_TranscriptMapper()->cdna2genomic(@_);
}


=head2 genomic2cdna

  Description: See Bio::EnsEMBL::TranscriptMapper::genomic2cdna

=cut

sub genomic2cdna {
  my $self = shift;
  return $self->get_TranscriptMapper->genomic2cdna(@_);
}


1;
