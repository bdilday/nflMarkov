
SHELL = /bin/sh

CLEAN_FILES = *.aux *.log *.bbl *.blg *.dvi
CLEANALL_FILES = $(CLEAN_FILES) nflMarkovDoc.ps nflMarkovDoc.pdf nflMarkov_k_of_n.ps nflMarkov_k_of_n.pdf

default: all
#	@ $(error error: do nothing by default)

all: nflMarkovDoc.pdf nflMarkov_k_of_n.pdf

clean-util:
	rm -f $(CLEAN_FILES) 


clean:
	rm -f $(CLEANALL_FILES) 


nflMarkovDoc.pdf : nflMarkovDoc.ps
	(ps2pdf nflMarkovDoc.ps)

nflMarkovDoc.ps : nflMarkovDoc.tex \
		nflMarkovDoc.bib 	
		(latex nflMarkovDoc; \
		bibtex nflMarkovDoc; \
		latex nflMarkovDoc; \
		latex nflMarkovDoc; \
		dvips -t letter -o nflMarkovDoc.ps nflMarkovDoc.dvi)

nflMarkov_k_of_n.pdf : nflMarkov_k_of_n.ps
	(ps2pdf nflMarkov_k_of_n.ps)

nflMarkov_k_of_n.ps : nflMarkov_k_of_n.tex \
		nflMarkov_k_of_n.bib 	
		(latex nflMarkov_k_of_n; \
		bibtex nflMarkov_k_of_n; \
		latex nflMarkov_k_of_n; \
		latex nflMarkov_k_of_n; \
		dvips -t letter -o nflMarkov_k_of_n.ps nflMarkov_k_of_n.dvi)

