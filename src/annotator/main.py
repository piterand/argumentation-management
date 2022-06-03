import base as be
import pipe as pe
import mspacy as msp
import mstanza as msa


def call_spacy(mydict, data, islist=False):
    spacy_dict = mydict["spacy_dict"]
    # load the pipeline
    annotated = msp.MySpacy(spacy_dict)
    # apply pipeline to data
    # data is not a list of sentences and will generate one doc object
    if not islist:
        annotated.apply_to(data)
        doc = annotated.doc
    else:
        # data is a list of sentences and will generate a list of doc objects
        doc = []
        for sentence in data:
            annotated.apply_to(sentence)
            doc.append(annotated.doc)
    # we should not need start ..?
    start = 0
    out_obj = msp.OutSpacy(doc, annotated.jobs, start=start, islist=islist)
    return out_obj


def call_stanza(mydict, data, islist=False):
    stanza_dict = mydict["stanza_dict"]
    if islist:
        stanza_dict["tokenize_no_ssplit"] = True
        # stanza needs tokenizer or tokenize_pretokenized=True
        # we want to avoid the latter so set the tokenizer
        # in some cases it could happen that tokenization differs from the tools
        # but we will walk that path when we get there
        stanza_dict["processors"] = "tokenize," + stanza_dict["processors"]
        # https://stanfordnlp.github.io/stanza/tokenize.html#start-with-pretokenized-text
        # set two continuous newlines so that sentences are not
        # split but we still use efficient capabilities
        data = [sent + "\n\n" for sent in data]
    # load the pipeline
    annotated = msa.MyStanza(stanza_dict)
    # apply pipeline to data
    annotated.apply_to(data)
    doc = annotated.doc
    # we should not need start ..?
    start = 0
    out_obj = msa.out_object_stanza(doc, annotated.jobs, start=start, islist=islist)
    return out_obj


call_tool = {"spacy": call_spacy, "stanza": call_stanza}


def assemble_out_stream(out_obj: list, out=list) -> list:
    # First the sentences
    stags = out_obj[0].get_stags()
    out_all = out[0]
    # Then iterate through objects and their output
    for i, my_obj in enumerate(out_obj):
        ptags = None
        ptags = ptags or out_obj[0].get_ptags()
    return out_all


if __name__ == "__main__":
    # load input dict
    mydict = be.prepare_run.load_input_dict("./src/annotator/input")
    # overwrite defaults for testing purposes
    # mydict["processing_option"] = "accurate"
    # mydict["processing_option"] = "fast"
    mydict["processing_option"] = "manual"
    # add a safety check if there are more tools than processors - TODO
    # mydict["tool"] = "spacy, stanza, stanza, stanza"
    mydict["tool"] = "spacy, spacy, stanza, stanza"
    # mydict["processing_type"] = "sentencize, pos  ,lemma, tokenize"
    mydict["processing_type"] = "sentencize, tokenize, pos, lemma"
    mydict["language"] = "en"
    # mydict["language"] = "de"
    mydict["advanced_options"]["output_dir"] = "./src/annotator/test/out/"
    mydict["advanced_options"]["corpus_dir"] = "./src/annotator/test/corpora/"
    mydict["advanced_options"]["registry_dir"] = "./src/annotator/test/registry/"
    # get the data to be processed
    data = be.prepare_run.get_text("./src/annotator/test/test_files/example_en.txt")
    # data = be.prepare_run.get_text("./src/annotator/test/test_files/example_de.txt")
    # validate the input dict
    be.prepare_run.validate_input_dict(mydict)
    # activate the input dict
    pe.SetConfig(mydict)
    # now we still need to add the order of steps - processors was ordered list
    # need to access that and tools to call tools one by one
    out_obj = []
    data_islist = False
    ptags = None
    stags = None
    my_todo_list = [[i, j] for i, j in zip(mydict["tool"], mydict["processing_type"])]
    # we need ordered "set"
    tools = set()  # a temporary lookup set
    ordered_tools = [
        mytool
        for mytool in mydict["tool"]
        if mytool not in tools and tools.add(mytool) is None
    ]
    for mytool in ordered_tools:
        # here we do the object generation
        # we do not want to call same tools multiple times
        # as that would re-run the nlp pipelines
        print(mytool)
        # if sentences are data, then we need to go through list
        # call specific routines
        my_out_obj = call_tool[mytool](mydict, data, data_islist)
        # out_obj.append(my_out_obj)
        if not data_islist:
            # the first tool will sentencize
            # all subsequent ones will use sentencized input
            # so the new data is sentences from first tool
            # however, this is now a list
            data = my_out_obj.sentences
            # do the sentence-level processing
            # assemble sentences and tokens - this is independent of tool
            out = my_out_obj.assemble_output_sent()
            # further annotation: done with same tool?
            if mydict["tool"].count(mytool) > 2:
                print("Further annotation with tool {} ...".format(mytool))
                out = my_out_obj.assemble_output_tokens(out)
            data_islist = True
            stags = my_out_obj.get_stags
        elif data_islist:
            # sentencized and tokenized data already processed
            # now token-level annotation
            out = my_out_obj.assemble_output_tokens(out)
            ptags_temp = my_out_obj.get_ptags()
            if ptags is not None:
                ptags += ptags_temp
            else:
                ptags = ptags_temp

    # stanza
    # the below for generating the output
    # for xml or vrt, let's stick with vrt for now - TODO
    # style = "STR"
    # out = out_obj[0].assemble_output_sent()
    # spacy
    # this replicates functionality, we need assemble_output_sent instead
    # out = out_obj[0].fetch_output(style)

    # Now stitch together the outputs
    # out_all = assemble_out_stream(out_obj, out)

    # write out to .vrt
    outfile = mydict["advanced_options"]["output_dir"] + mydict["corpus_name"]
    be.OutObject.write_vrt(outfile, out)
    # if not add:

    # we need to set the s and p attributes for all jobs
    # so stags and ptags need to be accumulated
    ptags = None
    stags = None
    encode_obj = be.encode_corpus(mydict)
    encode_obj.encode_vrt(ptags, stags)
    # elif add:
    #     encode_obj = be.encode_corpus(mydict)
    #     encode_obj.add_tags_to_corpus(mydict, ptags, stags)

    # to use pretokenized data - TODO
    # not sure why we need so many cases - TODO
    # if ret is False and style == "STR" and mydict is not None and add is False:
    # if not add:
    # elif ret is False and style == "STR" and mydict is not None and add is True:
    # elif ret is True:
    # "If ret is not set to True, a dict containing the encoding parameters is needed!"
