pytesseract.pytesseract.TesseractNotFoundError: This app has encountered an error. The original error message is redacted to prevent data leaks. Full error details have been recorded in the logs (if you're on Streamlit Cloud, click on 'Manage app' in the lower right of your app).
Traceback:
File "/mount/src/fmea/fmea_streamlit_app.py", line 225, in <module>
    df = generate_fmea()
File "/mount/src/fmea/fmea_streamlit_app.py", line 151, in generate_fmea
    file_text = extract_file_content(uploaded_files) if uploaded_files else ""
                ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^
File "/mount/src/fmea/fmea_streamlit_app.py", line 98, in extract_file_content
    combined_text += pytesseract.image_to_string(img) + "\n"
                     ~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^
File "/home/adminuser/venv/lib/python3.14/site-packages/pytesseract/pytesseract.py", line 486, in image_to_string
    return {
           ~
    ...<2 lines>...
        Output.STRING: lambda: run_and_get_output(*args),
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    }[output_type]()
    ~~~~~~~~~~~~~~^^
File "/home/adminuser/venv/lib/python3.14/site-packages/pytesseract/pytesseract.py", line 489, in <lambda>
    Output.STRING: lambda: run_and_get_output(*args),
                           ~~~~~~~~~~~~~~~~~~^^^^^^^
File "/home/adminuser/venv/lib/python3.14/site-packages/pytesseract/pytesseract.py", line 352, in run_and_get_output
    run_tesseract(**kwargs)
    ~~~~~~~~~~~~~^^^^^^^^^^
File "/home/adminuser/venv/lib/python3.14/site-packages/pytesseract/pytesseract.py", line 280, in run_tesseract
    raise TesseractNotFoundError()
