#!/usr/bin/perl
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

# EnsEMBL module for Bio::EnsEMBL::Variation::Utils::Sequence
#
#

=head1 NAME

Bio::EnsEMBL::Variation::Utils::VEP - Methods used by the Variant Effect Predictor

=head1 SYNOPSIS

  use Bio::EnsEMBL::Variation::Utils::VEP qw(configure);

  my $config = configure();

=head1 METHODS

=cut


use strict;
use warnings;

#package lib::consequence::VEP;

# module list
use Getopt::Long;
use FileHandle;
use File::Path qw(mkpath);
use Storable qw(nstore_fd fd_retrieve freeze thaw);
use Scalar::Util qw(weaken looks_like_number);
use Digest::MD5 qw(md5_hex);
use IO::Socket;
use IO::Select;
use Exporter;
use Data::Dumper;
use JSON;
use File::Basename qw(dirname);
use Cwd  qw(abs_path);
use lib dirname(dirname abs_path $0) . 'var/task/';
use consequence::VariationFeature;
use consequence::Transcript;
use consequence::TranscriptVariation;
use consequence::TranscriptVariationAllele;

my $config = {};
my $fastaLocation =  $ENV{'REFERENCE_LOCATION'};
my $outputLocation =  $ENV{'SVEP_REGIONS'};
my $tempLocation =  $ENV{'SVEP_TEMP'};
sub handle {
    my ($payload, $context) = @_;
    #print Dumper $payload;
    #my @data = decode_json($payload->{'Message'}); # This line is for individual lambda testing
    #my $data = decode_json($payload->{'Message'});
    #event['Records'][0]['Sns']['Message']
    my $event = $payload->{'Records'}[0];
    my $sns = $event->{'Sns'};
    ##########################################update
    #my @data = decode_json($sns->{'Message'});
    #my $id = $sns->{'MessageId'};
    my $message = decode_json($sns->{'Message'}); #might have to remove decode_json
    my @data = $message->{'snsData'};
    my $id = $message->{'APIid'};
    my $batchId = $message->{'batchID'};
    my $tempFileName = $message->{'tempFileName'};
    print("APIid is - $id\n");
    print("batchID is - $batchId\n");
    print("tempFileName is - $tempFileName\n");
    #############################################

    #print Dumper @data;
    my $chr = $data[0][0]->{'chrom'};
    print($chr);
    my $fasta ='Homo_sapiens.GRCh38.dna.chromosome.'.$chr.'.fa.gz';
    system("/opt/awscli/aws s3 cp $fastaLocation /tmp/ --recursive  --exclude '*'  --include '$fasta*'");
    my @results;
    while(@data){
      my $region = shift @data;
      foreach my $line (@{$region}){
        if ( scalar(@{$line->{'data'}}) == 1 && @{$line->{'data'}}[0] eq ''){
          next;
        }
        my $vep = parse_vcf($line);
        if(length $vep){
          push @results,$vep;
        }
      }
    }
    #my $filename = "/tmp/test.tsv";
    my $filename = "/tmp/".$id."_".$batchId.".tsv";
    open(my $fh, '>', $filename) or die "Could not open file '$filename' $!";
    print $fh join("\n", @results);
    close $fh;

    my $out = 's3://'.$outputLocation.'/';
    system("/opt/awscli/aws s3 cp $filename $out");
    print("Done Copying");
    my $tempOut = 's3://'.$tempLocation.'/'.$tempFileName;
    system("/opt/awscli/aws s3 rm $tempOut");
    print("Done Copying");
}

# parse a line of VCF input into a variation feature object
sub parse_vcf {
    my $line = shift;
    #print Dumper $line;
    my ($chr, $start, $end, $ref, $alt) = ($line->{'chrom'}, $line->{'pos'}, $line->{'pos'}, $line->{'ref'}, $line->{'alt'});
    #print("$chr\t$start\n");
    my @data = @{$line->{'data'}};
    if($data[0] eq ""){
      return;
    }
    my (@transcripts,@transcriptIds,@features) = ();

    # non-variant
    my $non_variant = 0;

    if($alt eq '.') {
        $non_variant = 1;
    }
    # adjust end coord
    $end += (length($ref) - 1);

    # find out if any of the alt alleles make this an insertion or a deletion
    my ($is_indel, $is_sub, $ins_count, $total_count);
    foreach my $alt_allele(split ',', $alt) {
        $is_indel = 1 if $alt_allele =~ /^[DI]/;
        $is_indel = 1 if length($alt_allele) != length($ref);
        $is_sub = 1 if length($alt_allele) == length($ref);
        $ins_count++ if length($alt_allele) > length($ref);
        $total_count++;
    }
    # multiple alt alleles?
    if($alt =~ /\,/) {
        if($is_indel) {
            my @alts;

            # find out if all the alts start with the same base
            # ignore "*"-types
            my %first_bases = map {substr($_, 0, 1) => 1} grep {!/\*/} ($ref, split(',', $alt));

            if(scalar keys %first_bases == 1) {
                $ref = substr($ref, 1) || '-';
                $start++;

                foreach my $alt_allele(split ',', $alt) {
                    $alt_allele = substr($alt_allele, 1) unless $alt_allele =~ /\*/;
                    $alt_allele = '-' if $alt_allele eq '';
                    push @alts, $alt_allele;
                }
            }
            else {
                push @alts, split(',', $alt);
            }

            $alt = join "/", @alts;
        }

        else {
            # for substitutions we just need to replace ',' with '/' in $alt
            $alt =~ s/\,/\//g;
        }
    }

    elsif($is_indel) {

        # insertion or deletion (VCF 4+)
        if(substr($ref, 0, 1) eq substr($alt, 0, 1)) {

            # chop off first base
            $ref = substr($ref, 1) || '-';
            $alt = substr($alt, 1) || '-';

            $start++;
        }
    }


    ######Start of my code for processing GTF #############
    while(@data){
      my $element = shift @data;
      if ($element =~ /transcript_id\s\"(\w+)\"\;/){
        push @transcriptIds, $1;
      }
      my @type =(split /\t/, $element);
      if ($type[2] eq "transcript"){
        push @transcripts,$element;
      }else{
        push @features,$element;
      }
    }
    my @uniqueTranscriptIds = do { my %seen; grep { !$seen{$_}++ } @transcriptIds };
    my @results;
    my %transcriptHash;
    $transcriptHash{$_}++ for (@uniqueTranscriptIds);

    foreach my $transcript (@transcripts){
      my @rows = (split /\t/, $transcript,-1);
      #print Dumper @rows;
      my %info = ();
      my ($seq,$length,$tr,$strand,$vf);

      foreach my $bit(split ';', ($rows[8])) {
          my ($key, $value) = split ' ', $bit, -1;    ##GTF info field passed by lambda contains key value separated by space.
          #print("$key\t$value\n");
          $value =~ s/"//g;
          $info{$key} = $value;
      }
      #print Dumper %info;
      foreach my $feature(@features){
        my @featurerows = (split /\t/, $feature, -1);
        my @info = (split ';', $featurerows[8],-1);
        my ($key, $value) = split ' ', $info[2],-1;
        $value =~ s/"//g;
        if($value eq $info{'transcript_id'}){
          if($featurerows[2] eq "exon"){
            $info{'exon'} = 1;
            $info{'exon_start'} = $featurerows[3];
            $info{'exon_end'} = $featurerows[4];
            my ($key1, $value1) = split ' ', $info[4],-1;
            $value1 =~ s/"//g;
            $info{'exon_number'} = $value1;
          }
          if($featurerows[2] eq "CDS"){
            $info{'CDS'} = 1;
            $info{'CDS_start'} = $featurerows[3];
            $info{'CDS_end'} = $featurerows[4];
            $info{'CDS_frame'} = $featurerows[7];
          }
          if($featurerows[2] eq "three_prime_utr"){
            $info{'three_prime_utr'} = 1;
            $info{'three_prime_utr_start'} = $featurerows[3];
            $info{'three_prime_utr_end'} = $featurerows[4];
          }
          if($featurerows[2] eq "five_prime_utr"){
            $info{'five_prime_utr'} = 1;
            $info{'five_prime_utr_start'} = $featurerows[3];
            $info{'five_prime_utr_end'} = $featurerows[4];
          }
        }
      }

      #print Dumper %info;
      #exit()

      my $original_alt = $alt;

      if($rows[6] =~ /^[+]/){
        $strand=1;
      }
      else{
        $strand = -1;
      }



      if(exists($info{'exon'})){

        # create VF object
        $vf = consequence::VariationFeature->new_fast({
            start          => $start,
            end            => $end,
            allele_string  => $non_variant ? $ref : $ref.'/'.$alt,
            strand         => $strand,
            map_weight     => 1,
            #adaptor        => $config->{vfa}, Need to get rid of this from variationFeature as Well
            variation_name => undef ,
            chr            => $chr,
            seq_region_start => $info{'exon_start'},
            seq_region_end => $info{'exon_end'},
            exon         => 1,
        });
        my $intron_boundary;

        if(exists($info{'CDS'})){
          my $location = $chr.':'.$info{'CDS_start'}.'-'.$info{'CDS_end'};
          my $fasta ='Homo_sapiens.GRCh38.dna.chromosome.'.$chr.'.fa.gz';
          my $file = '/tmp/'.$fasta;
          my @result = `./samtools faidx $file $location`;
          shift @result;
          $seq = join "", @result;
          $seq =~ s/[\r\n]+//g;
          $length = ($info{'CDS_end'}-$info{'CDS_start'},$info{'CDS_start'}-$info{'CDS_end'})[$info{'CDS_end'}-$info{'CDS_start'} < $info{'CDS_start'}-$info{'CDS_end'}];

          if( (($info{'CDS_end'} - $start) < 4) || (($start - $info{'CDS_start'}  ) < 4) ){
            $intron_boundary =1;
          }else{
            $intron_boundary =0;
          }

          $tr = consequence::Transcript->new_fast({
              stable_id          => $info{transcript_id},
              version            => $info{transcript_version},
              external_name  => $info{transcript_name},
              source         => $info{transcript_source},
              biotype     => $info{transcript_biotype},
              confidence => $info{transcript_support_level},
              start => $rows[3],
              end => $rows[4],
              cds => 1,
              intron_boundary => $intron_boundary,
              cdna_coding_start => $info{'CDS_start'},
              cdna_coding_end => $info{'CDS_end'},
              cds_frame => $info{'CDS_frame'},
              strand => $strand,
              seq => $seq,
              seq_length => $length,
              position => $start,
              ref_allele => $ref,
              alt_allele => $alt,
          });
        }elsif(exists($info{'three_prime_utr'}) ){
          if( (($info{'exon_end'} - $start) < 3) || (($start - $info{'exon_start'}  ) < 3) ){
            $intron_boundary =1;
          }else{
            $intron_boundary =0;
          }
          $tr = consequence::Transcript->new_fast({
              stable_id          => $info{transcript_id},
              version            => $info{transcript_version},
              external_name  => $info{transcript_name},
              source         => $info{transcript_source},
              biotype     => $info{transcript_biotype},
              confidence => $info{transcript_support_level},
              start => $rows[3],
              end => $rows[4],
              three_prime_utr => 1,
              exon_start => $info{'exon_start'},
              exon_end => $info{'exon_end'},
              strand => $strand,
              intron_boundary => $intron_boundary,
              splice_acceptor_variant => 1,
              #seq => $seq,
              #seq_length => $length,
              position => $start,
              ref_allele => $ref,
              alt_allele => $alt,
          });
        }elsif(exists($info{'five_prime_utr'})){
          if( (($info{'exon_end'} - $start) < 3) || (($start - $info{'exon_start'}  ) < 3) ){
            $intron_boundary =1;
          }else{
            $intron_boundary =0;
          }
          $tr = consequence::Transcript->new_fast({
              stable_id          => $info{transcript_id},
              version            => $info{transcript_version},
              external_name  => $info{transcript_name},
              source         => $info{transcript_source},
              biotype     => $info{transcript_biotype},
              confidence => $info{transcript_support_level},
              start => $rows[3],
              end => $rows[4],
              five_prime_utr => 1,
              exon_start => $info{'exon_start'},
              exon_end => $info{'exon_end'},
              strand => $strand,
              splice_donor_variant => 1,
              intron_boundary => $intron_boundary,
              #seq => $seq,
              #seq_length => $length,
              position => $start,
              ref_allele => $ref,
              alt_allele => $alt,
          });
        }else{
          if( (($info{'exon_end'} - $start) < 4) || (($start - $info{'exon_start'}  ) < 4) ){
            $intron_boundary =1;
          }else{
            $intron_boundary =0;
          }
          $tr = consequence::Transcript->new_fast({
              stable_id          => $info{transcript_id},
              version            => $info{transcript_version},
              external_name  => $info{transcript_name},
              source         => $info{transcript_source},
              biotype     => $info{transcript_biotype},
              confidence => $info{transcript_support_level},
              start => $rows[3],
              end => $rows[4],
              strand => $strand,
              exon_start => $info{'exon_start'},
              exon_end => $info{'exon_end'},
              intron_boundary => $intron_boundary,
              #seq => $seq,
              #seq_length => $length,
              position => $start,
              ref_allele => $ref,
              alt_allele => $alt,
          });
        }

      }else{
        # create VF object
        $vf = consequence::VariationFeature->new_fast({
            start          => $start,
            end            => $end,
            allele_string  => $non_variant ? $ref : $ref.'/'.$alt,
            strand         => $strand,
            map_weight     => 1,
            variation_name => undef ,
            chr            => $chr,
            intron         => 1,
        });
        $tr = consequence::Transcript->new_fast({
            stable_id          => $info{transcript_id},
            version            => $info{transcript_version},
            external_name  => $info{transcript_name},
            source         => $info{transcript_source},
            biotype     => $info{transcript_biotype},
            confidence => $info{transcript_support_level},
            start => $rows[3],
            end => $rows[4],
            strand => $strand,
            position => $start,
            ref_allele => $ref,
            alt_allele => $alt,
        });

      }

      # flag as non-variant
      $vf->{non_variant} = 1 if $non_variant;
      #print Dumper $tr;


      my $tv = $vf->add_TranscriptVariation(
              consequence::TranscriptVariation->new(
                  -variation_feature  => $vf,
                  -transcript         => $tr,
              )
      );

      my ($cons, $rank) = vf_to_consequences($vf);

      if(exists($tr->{'three_prime_utr'})){
        if( $cons eq 'intergenic_variant'){
          $cons = '3_prime_UTR_variant'
        }else{
        $cons = '3_prime_UTR_variant,'.$cons;
        }
      }
      if(exists($tr->{'five_prime_utr'})){
        if( $cons eq 'intergenic_variant'){
          $cons = '5_prime_UTR_variant'
        }else{
        $cons = '5_prime_UTR_variant,'.$cons;
        }
      }

      my $line = $rank."\t".('.')."\t".$chr.':'.$start.'-'.$end."\t".$alt."\t".$cons."\t".$info{gene_name}."\t".$info{gene_id}."\t".$rows[2]."\t".
      $info{transcript_id}.".".$info{transcript_version}."\t".$info{transcript_biotype}."\t".($info{'exon_number'} || '-')."\t".
      ($tv->{'feature'}{'aa'} || '-')."\t".($tv->{'feature'}{'codons'} || '-')."\t".$strand."\t".($info{transcript_support_level}|| '-');
      #print($result1);
      if(length $tr->{warning}){
        $line = $line."\t".$tr->{warning};
      }
      push @results,$line;
      #print("$rank\n");

    }
    my @sorted = sort { (split('\t', $a))[0] <=> (split('\t', $b))[0] } @results;
    return join("\n", @sorted);

    #print Dumper @sorted;

    #my $PutObjectOutput = $s3->PutObject(
    #  Bucket             => $outputLocation,
    #  Key                => $filename,                 # OPTIONAL
    #  Body               => join("\n", @sorted),
    #  );
    #print($PutObjectOutput->ETag);

}

# takes a variation feature and returns ready to print consequence information
sub vf_to_consequences {
  my $vf = shift;
  my $vf_ref = ref($vf);

  my @return = ();

  my $allele_method = defined($config->{process_ref_homs}) ? 'get_all_' : 'get_all_alternate_';

  # get all VFOAs
  # need to be sensitive to whether --regulatory or --coding_only is switched on
  my $vfos;
  my $method = $allele_method.'VariationFeatureOverlapAlleles';

  # include regulatory stuff?
  if(!defined $config->{coding_only} && defined $config->{regulatory}) {
    $vfos = $vf->get_all_VariationFeatureOverlaps;
  }
  # otherwise just get transcript & intergenic ones
  else {
    @$vfos = grep {defined($_)} (
      @{$vf->get_all_TranscriptVariations}
#      $vf->get_IntergenicVariation
    );
  }

  # grep out non-coding?
  @$vfos = grep {$_->can('affects_cds') && $_->affects_cds} @$vfos if defined($config->{coding_only});
  #print Dumper $vfos;
  # get alleles
  my @vfoas = map {@{$_->$method}} @{$vfos};

    my $line;
    my $term_method = 'SO_term';

    my @ocs = sort {$a->rank <=> $b->rank} map {@{$_->get_all_OverlapConsequences}} @vfoas;

    #print Dumper @ocs;
    #print($vfos->{'transcript'}->{'stable_id'});
    #print("ARE WE HERE\n");
    $line->{Consequence} = join ",", keys %{{map {$_ => 1} map {$_->$term_method || $_->SO_term} @ocs}};
    #$line = $ocs[0]->$term_method || $ocs[0]->SO_term;
    my $conLine = $line->{Consequence};
    my $rank = $ocs[0]->rank;
    #print Dumper $line;

    #push @return, $line;
    #print("$conLine\n");

  return $conLine, $rank;
}



1;
